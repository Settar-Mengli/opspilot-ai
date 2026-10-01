"""Bounded Ask agent loop (D-014 / D-031 / D-032)."""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import Any

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
from opspilot.llm.types import Message
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


def _complete_json_with_timeout(
    gw: BudgetAwareGateway,
    *,
    messages: list[Message],
    timeout_s: float,
) -> AgentTurn:
    """Bound wall time for a sync gateway call without blocking on the abandoned worker.

    Budget debit happens inside the gateway before the provider body runs; a timeout
    after debit still counts as a consumed attempt. The worker is abandoned via
    shutdown(wait=False) so the Ask loop is not blocked past timeout_s.
    """
    executor = ThreadPoolExecutor(max_workers=1)

    def _call() -> AgentTurn:
        return gw.complete_json(
            task="ask",
            messages=messages,
            schema=AgentTurn,
            max_tokens=800,
        )

    fut = executor.submit(_call)
    try:
        return fut.result(timeout=timeout_s)
    except FuturesTimeoutError as exc:
        raise StepTimeoutError("step_timeout") from exc
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


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
        provider_list,
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
            turn = _complete_json_with_timeout(gw, messages=messages, timeout_s=step_timeout_s)
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
        messages.append(
            Message(
                role="user",
                content=tool_result_untrusted(tool_name, tool_blob),
            )
        )

    yield AgentEvent(
        "error",
        rid,
        {"code": "step_cap", "message": "Ask step budget exhausted before a final answer."},
    )
