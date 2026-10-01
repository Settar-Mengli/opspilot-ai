"""Bounded Ask agent loop (D-014 / D-031 / D-032)."""

from __future__ import annotations

import json
import os
import threading
from collections.abc import Callable, Iterator
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from opspilot.agent.events import AgentEvent
from opspilot.agent.safety import tool_result_untrusted
from opspilot.agent.tool_protocol import TOOL_SYSTEM_FRAGMENT, AgentTurn
from opspilot.agent.tools import execute_tool
from opspilot.llm.gateway import session_attempt_recorder
from opspilot.llm.prompt_safety import UNTRUSTED_SYSTEM_POLICY
from opspilot.llm.providers.base import LlmProvider
from opspilot.llm.routed import BudgetAwareGateway
from opspilot.llm.routing import build_providers
from opspilot.llm.types import Message, ProviderResult, TaskName
from opspilot.services._llm import compact_triage_lines

CancelCheck = Callable[[], bool]


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

        tool_blob = json.dumps(result, ensure_ascii=False)[:2000]
        messages.append(
            Message(
                role="assistant",
                content=json.dumps({"kind": "tool", "tool": tool_name, "args": args}),
            )
        )
        messages.append(Message(role="user", content=tool_result_untrusted(tool_name, tool_blob)))

    yield AgentEvent(
        "error",
        rid,
        {"code": "step_cap", "message": "Ask step budget exhausted before a final answer."},
    )
