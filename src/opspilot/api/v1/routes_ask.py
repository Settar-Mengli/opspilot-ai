"""Ask SSE stream (D-032)."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Callable, Iterator
from typing import Any

import anyio
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, select, update
from sqlalchemy.orm import Session

from opspilot.agent.events import event_dict
from opspilot.agent.loop import CancelCheck, run_ask_agent
from opspilot.api.csrf import require_csrf_origin
from opspilot.api.deps import get_db_session
from opspilot.api.schemas import AskStreamRequest
from opspilot.llm.github_mcp_auth import OperatorGitHubMcpAuth
from opspilot.llm.operator_auth import OperatorAnthropicAuth
from opspilot.llm.routing import build_providers
from opspilot.persistence.models import LlmCallRow
from opspilot.persistence.repositories import oauth_credentials
from opspilot.services.operator_session import COOKIE_NAME, verify_session

router = APIRouter(tags=["ask"])
_logger = logging.getLogger("opspilot.api.ask")

PollerStop = Callable[[], None]


def _request_id(http_request: Request) -> str | None:
    rid = getattr(http_request.state, "request_id", None)
    if isinstance(rid, str) and rid.strip():
        return rid.strip()
    return None


def _google_connected(session: Session) -> bool:
    return oauth_credentials.is_connected(session, provider="google")


def _latest_triage_records(session: Session) -> list[dict[str, Any]]:
    from opspilot.services.triage_overlay import latest_triage_with_overlay

    return latest_triage_with_overlay(session, gmail_only=_google_connected(session))


def _operator_email(request: Request) -> str | None:
    sess = verify_session(request.cookies.get(COOKIE_NAME))
    return sess.email if sess else None


def _sse_line(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _stamp_ttft(session: Session, request_id: str, ttft_ms: int) -> None:
    row = session.execute(
        select(LlmCallRow.id).where(LlmCallRow.request_id == request_id).order_by(desc(LlmCallRow.id)).limit(1)
    ).scalar_one_or_none()
    if row is None:
        return
    session.execute(update(LlmCallRow).where(LlmCallRow.id == row).values(ttft_ms=ttft_ms))
    session.flush()


def _disconnect_poller(http_request: Request) -> tuple[CancelCheck, PollerStop]:
    """Poll request.is_disconnected; return cancel_check + stop().

    Sync StreamingResponse runs the generator in a worker thread; cancel_check uses
    anyio.from_thread.run to probe disconnection on the event loop. stop() cancels
    the background watcher task on every stream exit path.
    """
    disconnected = {"v": False}
    state: dict[str, Any] = {"task": None}

    async def _watch() -> None:
        try:
            while True:
                if await http_request.is_disconnected():
                    disconnected["v"] = True
                    return
                await asyncio.sleep(0.05)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 — narrow log; treat as disconnect
            _logger.warning(
                "ask_disconnect_poller_error error_code=%s",
                type(exc).__name__,
            )
            disconnected["v"] = True

    try:
        loop = asyncio.get_running_loop()
        state["task"] = loop.create_task(_watch())
    except RuntimeError:
        pass

    def cancel_check() -> bool:
        if disconnected["v"]:
            return True
        try:
            if anyio.from_thread.run(http_request.is_disconnected):
                disconnected["v"] = True
                return True
        except Exception as exc:  # noqa: BLE001
            _logger.warning(
                "ask_disconnect_probe_error error_code=%s",
                type(exc).__name__,
            )
        return bool(disconnected["v"])

    def stop() -> None:
        task = state.get("task")
        if task is None:
            return
        if not task.done():
            task.cancel()

        async def _drain() -> None:
            try:
                await task
            except asyncio.CancelledError:
                return
            except Exception:  # noqa: BLE001 — drain only
                return

        try:
            loop = task.get_loop()
        except Exception:  # noqa: BLE001
            return
        if loop is None or loop.is_closed():
            return
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is not None and running is loop:
            # Same loop: schedule drain; do not block the loop thread.
            loop.create_task(_drain())
            return
        try:
            fut = asyncio.run_coroutine_threadsafe(_drain(), loop)
            fut.result(timeout=1.0)
        except Exception:  # noqa: BLE001 — best-effort drain
            return

    stop.task = state.get("task")  # type: ignore[attr-defined]
    return cancel_check, stop


@router.post("/ask/stream")
def ask_stream(
    payload: AskStreamRequest,
    http_request: Request,
    session: Session = Depends(get_db_session),
) -> StreamingResponse:
    require_csrf_origin(http_request)
    rid = _request_id(http_request) or "ask"
    records = _latest_triage_records(session)
    gmail_only = _google_connected(session)
    operator_email = _operator_email(http_request)
    cookie = http_request.cookies.get(COOKIE_NAME)
    operator_auth = OperatorAnthropicAuth.from_session(verify_session(cookie))
    github_mcp_auth = OperatorGitHubMcpAuth.from_session(verify_session(cookie))
    # Free path unchanged: omit providers when unauthenticated so loop.build_providers
    # (and existing hermetic monkeypatches) remain the visitor/default path.
    providers = (
        build_providers(operator_auth=operator_auth, session=session, task="ask") if operator_auth is not None else None
    )
    history = [{"role": h.role, "content": h.content} for h in payload.history]
    cancel_check, stop_poller = _disconnect_poller(http_request)

    def event_gen() -> Iterator[str]:
        ttft_done = False
        started = time.perf_counter()
        try:
            for event in run_ask_agent(
                question=payload.question,
                assistant_name=payload.assistant_name,
                triage_records=records,
                history=history,
                session=session,
                request_id=rid,
                gmail_only=gmail_only,
                operator_email=operator_email,
                providers=providers,
                cancel_check=cancel_check,
                github_mcp_auth=github_mcp_auth,
            ):
                if event.type == "token" and not ttft_done:
                    ttft_ms = int((time.perf_counter() - started) * 1000)
                    _stamp_ttft(session, rid, ttft_ms)
                    ttft_done = True
                yield _sse_line(event_dict(event))
            session.commit()
        except Exception:  # noqa: BLE001
            session.rollback()
            yield _sse_line({"type": "error", "request_id": rid, "code": "stream_failed", "message": "Ask failed."})
        finally:
            stop_poller()

    return StreamingResponse(event_gen(), media_type="text/event-stream")
