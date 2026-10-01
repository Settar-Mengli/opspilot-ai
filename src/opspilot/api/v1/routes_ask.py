"""Ask SSE stream (D-032)."""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Iterator
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, select, update
from sqlalchemy.orm import Session

from opspilot.agent.events import event_dict
from opspilot.agent.loop import CancelCheck, run_ask_agent
from opspilot.api.csrf import require_csrf_origin
from opspilot.api.deps import get_db_session
from opspilot.api.schemas import AskStreamRequest
from opspilot.persistence.models import LlmCallRow, TriageDecisionRow, WorkItemRow
from opspilot.persistence.repositories import oauth_credentials
from opspilot.services.operator_session import COOKIE_NAME, verify_session

router = APIRouter(tags=["ask"])


def _request_id(http_request: Request) -> str | None:
    rid = getattr(http_request.state, "request_id", None)
    if isinstance(rid, str) and rid.strip():
        return rid.strip()
    return None


def _google_connected(session: Session) -> bool:
    return oauth_credentials.is_connected(session, provider="google")


def _latest_triage_records(session: Session) -> list[dict[str, Any]]:
    stmt = (
        select(TriageDecisionRow, WorkItemRow)
        .join(WorkItemRow, TriageDecisionRow.work_item_id == WorkItemRow.id)
        .order_by(desc(TriageDecisionRow.id))
    )
    if _google_connected(session):
        stmt = stmt.where(WorkItemRow.source_type == "gmail")
    result = session.execute(stmt)
    seen: set[str] = set()
    payload: list[dict[str, Any]] = []
    for decision, work_item in result.all():
        if decision.work_item_id in seen:
            continue
        seen.add(decision.work_item_id)
        payload.append(
            {
                "id": decision.work_item_id,
                "subject_or_title": work_item.subject_or_title,
                "urgency": decision.urgency,
                "urgency_reason": decision.urgency_reason,
                "category": decision.category,
                "category_reason": decision.category_reason,
                "sentiment": decision.sentiment,
                "sentiment_reason": decision.sentiment_reason,
            }
        )
    return payload


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


def _disconnect_poller(http_request: Request) -> CancelCheck:
    """Return a cancel_check that polls request.is_disconnected without awaiting in the loop."""

    disconnected = {"v": False}

    async def _watch() -> None:
        try:
            while True:
                if await http_request.is_disconnected():
                    disconnected["v"] = True
                    return
                await asyncio.sleep(0.05)
        except Exception:  # noqa: BLE001
            disconnected["v"] = True

    # Schedule watcher when an event loop is running (ASGI); TestClient may lack one.
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_watch())
    except RuntimeError:
        pass

    def cancel_check() -> bool:
        return bool(disconnected["v"])

    return cancel_check


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
    history = [{"role": h.role, "content": h.content} for h in payload.history]
    cancel_check = _disconnect_poller(http_request)

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
                cancel_check=cancel_check,
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

    return StreamingResponse(event_gen(), media_type="text/event-stream")
