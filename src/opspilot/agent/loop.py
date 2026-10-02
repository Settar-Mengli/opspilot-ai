"""Bounded Ask agent loop (D-014 / D-031 / D-032)."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
from collections.abc import Callable, Iterator
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from opspilot.agent.events import AgentEvent
from opspilot.agent.safety import tool_result_untrusted
from opspilot.agent.tool_protocol import TOOL_SYSTEM_FRAGMENT, AgentTurn, tool_error_hint
from opspilot.agent.tools import execute_tool
from opspilot.llm.errors import LlmPolicyDenied
from opspilot.llm.gateway import session_attempt_recorder
from opspilot.llm.policy import llm_allowed
from opspilot.llm.prompt_safety import UNTRUSTED_SYSTEM_POLICY
from opspilot.llm.providers.base import LlmProvider
from opspilot.llm.routed import BudgetAwareGateway
from opspilot.llm.routing import build_providers
from opspilot.llm.types import Message, ProviderResult, TaskName
from opspilot.services._llm import compact_triage_lines

CancelCheck = Callable[[], bool]
_logger = logging.getLogger("opspilot.api.ask")


def _args_hash(args: dict[str, Any]) -> str:
    blob = json.dumps(args, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def _id_prefix_len(args: dict[str, Any]) -> tuple[int, str]:
    raw = str(args.get("work_item_id") or args.get("id") or "")
    if not raw:
        return 0, ""
    return len(raw), raw[:8]


def _model_tool_feedback(tool_name: str, result: dict[str, Any]) -> str:
    """UNTRUSTED tool JSON plus optional trusted hint line (content-free)."""
    payload = dict(result)
    hint = None
    if not payload.get("ok"):
        hint = tool_error_hint(str(payload.get("error") or "") or None)
        if hint:
            payload["hint"] = hint
    blob = json.dumps(payload, ensure_ascii=False)[:2000]
    wrapped = tool_result_untrusted(tool_name, blob)
    if hint:
        return f"{wrapped}\nHint (trusted): {hint}"
    return wrapped


def _log_ask_tool(
    *,
    request_id: str,
    step: int,
    provider: str | None,
    model: str | None,
    tool: str,
    args: dict[str, Any],
    result: dict[str, Any],
) -> None:
    id_len, id_prefix = _id_prefix_len(args)
    err = result.get("error")
    _logger.info(
        "ask_tool request_id=%s step=%s provider=%s model=%s tool=%s arg_keys=%s id_len=%s id_prefix=%s ok=%s error=%s",
        request_id,
        step,
        provider or "-",
        model or "-",
        tool,
        ",".join(sorted(str(k) for k in args.keys())),
        id_len,
        id_prefix or "-",
        bool(result.get("ok")),
        str(err)[:64] if err is not None else "-",
    )


class StepTimeoutError(TimeoutError):
    """Provider step exceeded OPSPILOT_ASK_STEP_TIMEOUT_S."""


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return max(1, int(raw))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return max(0.1, float(raw))
    except ValueError:
        return default


def _history_messages(history: list[dict[str, str]] | None, *, max_turns: int = 10) -> list[Message]:
    if not history:
        return []
    trimmed = history[-max_turns:]
    out: list[Message] = []
    for turn in trimmed:
        role = turn.get("role") or "user"
        text = (turn.get("content") or turn.get("text") or "")[:2000]
        if role not in {"user", "assistant", "system"}:
            role = "user"
        out.append(Message(role=role, content=text))  # type: ignore[arg-type]
    return out


def _tool_end_payload(tool_name: str, result: dict[str, Any]) -> dict[str, Any]:
    """Minimized tool_end: name + ok + optional error code only (D-032)."""
    payload: dict[str, Any] = {"tool": tool_name, "ok": bool(result.get("ok"))}
    err = result.get("error")
    if err is not None:
        payload["error"] = str(err)[:64]
    return payload


def _call_with_wall_timeout[T](fn: Callable[[], T], timeout_s: float) -> T:
    """Run sync fn in a daemon thread; bound wall time without joining forever.

    Daemon threads do not block process/pytest exit. Only the provider body should
    run here — never the SQLAlchemy session / budget path.
    """
    box: dict[str, Any] = {}

    def _target() -> None:
        try:
            box["ok"] = fn()
        except Exception as exc:  # noqa: BLE001 — re-raised on caller thread
            box["err"] = exc

    thread = threading.Thread(target=_target, name="ask-step-timeout", daemon=True)
    thread.start()
    thread.join(timeout=timeout_s)
    if thread.is_alive():
        raise StepTimeoutError("step_timeout")
    if "err" in box:
        raise box["err"]
    return box["ok"]  # type: ignore[no-any-return]


class _TimeoutProvider:
    """Wrap a provider so complete/complete_json honor a wall-clock timeout."""

    def __init__(self, inner: LlmProvider, timeout_s: float) -> None:
        self._inner = inner
        self._timeout_s = timeout_s

    @property
    def name(self) -> str:
        return self._inner.name

    def complete(
        self,
        *,
        task: TaskName,
        messages: list[Message],
        max_tokens: int,
        model: str | None = None,
    ) -> ProviderResult:
        return _call_with_wall_timeout(
            lambda: self._inner.complete(task=task, messages=messages, max_tokens=max_tokens, model=model),
            self._timeout_s,
        )

    def complete_json(
        self,
        *,
        task: TaskName,
        messages: list[Message],
        schema: type[BaseModel],
        max_tokens: int,
        model: str | None = None,
        repair_hint: str | None = None,
        force_json_object: bool = False,
        temperature: float | None = None,
    ) -> ProviderResult:
        return _call_with_wall_timeout(
            lambda: self._inner.complete_json(
                task=task,
                messages=messages,
                schema=schema,
                max_tokens=max_tokens,
                model=model,
                repair_hint=repair_hint,
                force_json_object=force_json_object,
                temperature=temperature,
            ),
            self._timeout_s,
        )

    def stream(self, **kwargs):  # type: ignore[no-untyped-def]
        return self._inner.stream(**kwargs)


def run_ask_agent(
    *,
    question: str,
    assistant_name: str = "OpsPilot",
    triage_records: list[dict[str, Any]] | None = None,
    history: list[dict[str, str]] | None = None,
    session: Session,
    request_id: str | None = None,
    gmail_only: bool = False,
    operator_email: str | None = None,
    providers: list[LlmProvider] | None = None,
    cancel_check: CancelCheck | None = None,
) -> Iterator[AgentEvent]:
    """Yield agent events until final/error. Enforces step and provider-call caps."""
    rid = (request_id or "ask").strip() or "ask"
    max_steps = _env_int("OPSPILOT_ASK_MAX_STEPS", 5)
    max_calls = _env_int("OPSPILOT_ASK_MAX_PROVIDER_CALLS", 8)
    step_timeout_s = _env_float("OPSPILOT_ASK_STEP_TIMEOUT_S", 30.0)

    if not question or not question.strip():
        yield AgentEvent("final", rid, {"answer": "I didn't catch a question. What would you like to know?"})
        return

    # Default path respects FORCE_RULES / LLM_DISABLE before constructing providers.
    if providers is None and not llm_allowed():
        yield AgentEvent(
            "error",
            rid,
            {
                "code": "llm_policy_denied",
                "message": "Ask unavailable: remote LLM disabled by policy.",
            },
        )
        return

    provider_list = providers if providers is not None else build_providers()
    if not provider_list:
        yield AgentEvent(
            "error",
            rid,
            {
                "code": "no_provider",
                "message": "Ask unavailable: no free-tier provider configured.",
            },
        )
        return

    timed_providers: list[LlmProvider] = [_TimeoutProvider(p, step_timeout_s) for p in provider_list]

    system = (
        f"You are {assistant_name}, OpsPilot chief of staff. Calm, concise, first person. "
        f"{UNTRUSTED_SYSTEM_POLICY} {TOOL_SYSTEM_FRAGMENT}\n"
        f"Context:\n{compact_triage_lines(triage_records or [])}"
    )
    messages: list[Message] = [
        Message(role="system", content=system),
        *_history_messages(history),
        Message(role="user", content=question.strip()[:2000]),
    ]

    recorder = session_attempt_recorder(session)
    gw = BudgetAwareGateway(
        timed_providers,
        session=session,
        recorder=recorder,
        observe=True,
        request_id=rid,
    )
    provider_calls = 0
    first_token = True
    last_fail_key: tuple[str, str, str] | None = None
    fail_streak = 0

    for step in range(max_steps):
        if cancel_check and cancel_check():
            yield AgentEvent("error", rid, {"code": "aborted", "message": "Ask cancelled."})
            return
        if provider_calls >= max_calls:
            yield AgentEvent(
                "error",
                rid,
                {"code": "provider_call_cap", "message": "Ask provider call budget exhausted."},
            )
            return

        provider_calls += 1
        try:
            # Gateway (budget debit + record) stays on this thread; provider body is timed.
            turn = gw.complete_json(
                task="ask",
                messages=messages,
                schema=AgentTurn,
                max_tokens=800,
            )
        except StepTimeoutError:
            yield AgentEvent("error", rid, {"code": "step_timeout", "message": "Ask step timed out."})
            return
        except LlmPolicyDenied:
            yield AgentEvent(
                "error",
                rid,
                {
                    "code": "llm_policy_denied",
                    "message": "Ask unavailable: remote LLM disabled by policy.",
                },
            )
            return
        except Exception:  # noqa: BLE001 — soft boundary; never leak exception text
            yield AgentEvent("error", rid, {"code": "ask_failed", "message": "Ask failed."})
            return

        if cancel_check and cancel_check():
            yield AgentEvent("error", rid, {"code": "aborted", "message": "Ask cancelled."})
            return

        if turn.kind == "final":
            answer = (turn.final or "").strip() or "I did not get a response. Please try again."
            if first_token:
                yield AgentEvent("token", rid, {"text": answer, "ttft": True})
                first_token = False
            else:
                yield AgentEvent("token", rid, {"text": answer})
            yield AgentEvent("final", rid, {"answer": answer, "steps": step + 1, "provider_calls": provider_calls})
            return

        tool_name = turn.tool or ""
        args = turn.args or {}
        yield AgentEvent("tool_start", rid, {"tool": tool_name, "args": args})
        result = execute_tool(
            tool_name,
            args,
            session=session,
            gmail_only=gmail_only,
            operator_email=operator_email,
            request_id=rid,
        )
        _log_ask_tool(
            request_id=rid,
            step=step + 1,
            provider=getattr(gw, "last_provider", None),
            model=getattr(gw, "last_model", None),
            tool=tool_name,
            args=args,
            result=result,
        )
        yield AgentEvent("tool_end", rid, _tool_end_payload(tool_name, result))
        if tool_name == "draft_reply" and result.get("ok") and result.get("draft_id"):
            yield AgentEvent(
                "draft",
                rid,
                {
                    "draft_id": result["draft_id"],
                    "subject": result.get("subject", ""),
                    "body": result.get("body", ""),
                    "to_addrs": result.get("to_addrs", ""),
                    "approve_ready": False,
                },
            )

        if not result.get("ok"):
            fail_key = (tool_name, _args_hash(args), str(result.get("error") or ""))
            if fail_key == last_fail_key:
                fail_streak += 1
            else:
                last_fail_key = fail_key
                fail_streak = 1
            if fail_streak >= 2:
                soft = (
                    "I could not complete that tool call after repeating the same failure. "
                    "Try again with the exact work item id from search, or rephrase."
                )
                yield AgentEvent(
                    "error",
                    rid,
                    {
                        "code": "tool_repeat_failure",
                        "message": soft,
                        "tool": tool_name,
                        "error": str(result.get("error") or "")[:64],
                    },
                )
                if first_token:
                    yield AgentEvent("token", rid, {"text": soft, "ttft": True})
                else:
                    yield AgentEvent("token", rid, {"text": soft})
                yield AgentEvent(
                    "final",
                    rid,
                    {
                        "answer": soft,
                        "code": "tool_repeat_failure",
                        "steps": step + 1,
                        "provider_calls": provider_calls,
                    },
                )
                return
        else:
            last_fail_key = None
            fail_streak = 0

        messages.append(
            Message(
                role="assistant",
                content=json.dumps({"kind": "tool", "tool": tool_name, "args": args}),
            )
        )
        messages.append(Message(role="user", content=_model_tool_feedback(tool_name, result)))

    yield AgentEvent(
        "error",
        rid,
        {"code": "step_cap", "message": "Ask step budget exhausted before a final answer."},
    )
