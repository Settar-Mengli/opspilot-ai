"""/api/v1 route handlers (Postgres SoT)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from opspilot.api.deps import get_db_session
from opspilot.api.paths import RAW_INPUT_DIR
from opspilot.api.schemas import (
    AskRequest,
    EveningSummaryRequest,
    InsightsRequest,
    RunPipelineRequest,
    safe_error,
    safe_history_metadata,
)
from opspilot.api.services.persist import persist_pipeline_result
from opspilot.api.services.pipeline import execute_pipeline
from opspilot.capabilities.registry import get_all_capabilities, get_capability
from opspilot.config.settings import ai_settings
from opspilot.persistence.models import RunArtifactRow, RunRow, TriageDecisionRow, WorkItemRow
from opspilot.services.ask import answer_question
from opspilot.services.evening import generate_evening_summary
from opspilot.services.insights import generate_insights

router = APIRouter(prefix="/api/v1")


def _settings_payload(session: Session | None = None) -> dict[str, object]:
    from opspilot.persistence.repositories import oauth_credentials
    from opspilot.services.operator_session import demo_mode_enabled

    google_connected = False
    if session is not None:
        google_connected = oauth_credentials.is_connected(session, provider="google")
    return {
        "provider": ai_settings.provider,
        "model": ai_settings.model,
        "api_key_set": bool(ai_settings.api_key),
        "demo_mode": demo_mode_enabled(),
        "google_connected": google_connected,
    }


def _artifact_text(session: Session, run_id: str, logical_name: str) -> str | None:
    result = session.execute(
        select(RunArtifactRow).where(
            RunArtifactRow.run_id == run_id,
            RunArtifactRow.name == logical_name,
        )
    )
    row = result.scalar_one_or_none()
    return None if row is None else row.content


def _latest_triage_records(session: Session) -> list[dict[str, Any]]:
    """Latest triage decisions joined to work items (same shape as GET /triage)."""
    result = session.execute(
        select(TriageDecisionRow, WorkItemRow)
        .join(WorkItemRow, TriageDecisionRow.work_item_id == WorkItemRow.id)
        .order_by(desc(TriageDecisionRow.id))
    )
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


@router.get("/health", response_class=PlainTextResponse)
def health() -> str:
    return "ok"


@router.get("/settings", response_class=JSONResponse)
def get_settings(session: Session = Depends(get_db_session)) -> dict[str, object]:
    return _settings_payload(session)


@router.post("/runs")
def create_run(
    req: RunPipelineRequest,
    session: Session = Depends(get_db_session),
) -> dict[str, object]:
    result = execute_pipeline(req)
    sample = RAW_INPUT_DIR / Path(req.input_file).name
    run_id = persist_pipeline_result(session, result, sample_input=sample)
    return {
        "status": "success",
        "stdout": f"OpsPilot AI run completed.\nrun_id: {run_id}",
        "run_id": run_id,
    }


@router.get("/runs", response_class=JSONResponse)
def list_runs(
    session: Session = Depends(get_db_session),
    limit: int = 50,
    cursor: str | None = None,
) -> list[dict[str, Any]]:
    """List runs newest-first. Default limit 50, max 100. Response stays a JSON array."""
    page_size = min(max(limit, 1), 100)
    query = select(RunRow).order_by(desc(RunRow.finished_at), desc(RunRow.run_id))
    if cursor:
        cur = session.get(RunRow, cursor)
        if cur is not None:
            query = query.where(
                (RunRow.finished_at < cur.finished_at)
                | ((RunRow.finished_at == cur.finished_at) & (RunRow.run_id < cur.run_id))
            )
    rows = session.execute(query.limit(page_size)).scalars().all()
    return [safe_history_metadata(dict(row.metadata_json or {"run_id": row.run_id})) for row in rows]


@router.get("/runs/{run_id}", response_class=JSONResponse)
def get_run(run_id: str, session: Session = Depends(get_db_session)) -> dict[str, Any]:
    row = session.get(RunRow, run_id)
    if row is None:
        raise safe_error(404, "run_not_found", "Run not found.")
    return safe_history_metadata(dict(row.metadata_json or {"run_id": row.run_id}))


@router.get("/triage", response_class=JSONResponse)
def get_triage(
    session: Session = Depends(get_db_session),
    limit: int = 100,
    cursor: str | None = None,
) -> list[dict[str, Any]]:
    """Latest triage decisions with AI-05 lite subject_or_title from WorkItem."""
    page_size = max(1, min(limit, 100))
    records = _latest_triage_records(session)
    if cursor:
        try:
            idx = next(i for i, r in enumerate(records) if r.get("id") == cursor)
            records = records[idx + 1 :]
        except StopIteration:
            records = []
    return records[:page_size]


@router.get("/runs/{run_id}/triage", response_class=JSONResponse)
def get_run_triage(run_id: str, session: Session = Depends(get_db_session)) -> list[Any]:
    if session.get(RunRow, run_id) is None:
        raise safe_error(404, "run_not_found", "Run not found.")
    content = _artifact_text(session, run_id, "triage_results")
    if content is None:
        raise safe_error(404, "artifact_not_found", "Run triage artifact not found.")
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise safe_error(500, "artifact_read_failed", "Failed to read run triage artifact.") from exc
    if not isinstance(payload, list):
        raise safe_error(500, "artifact_read_failed", "Failed to read run triage artifact.")
    return payload


@router.get("/briefing", response_class=PlainTextResponse)
def get_briefing(session: Session = Depends(get_db_session)) -> str:
    result = session.execute(
        select(RunArtifactRow).where(RunArtifactRow.name == "daily_briefing").order_by(desc(RunArtifactRow.id)).limit(1)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise safe_error(404, "briefing_not_found", "Briefing not found.")
    return row.content


@router.get("/runs/{run_id}/briefing", response_class=PlainTextResponse)
def get_run_briefing(run_id: str, session: Session = Depends(get_db_session)) -> str:
    if session.get(RunRow, run_id) is None:
        raise safe_error(404, "run_not_found", "Run not found.")
    content = _artifact_text(session, run_id, "daily_briefing")
    if content is None:
        raise safe_error(404, "artifact_not_found", "Run briefing artifact not found.")
    return content


@router.get("/ai-briefing", response_class=PlainTextResponse)
def get_ai_briefing(session: Session = Depends(get_db_session)) -> str:
    result = session.execute(
        select(RunArtifactRow).where(RunArtifactRow.name == "ai_briefing").order_by(desc(RunArtifactRow.id)).limit(1)
    )
    row = result.scalar_one_or_none()
    if row is not None:
        return row.content
    fallback = session.execute(
        select(RunArtifactRow).where(RunArtifactRow.name == "daily_briefing").order_by(desc(RunArtifactRow.id)).limit(1)
    ).scalar_one_or_none()
    if fallback is None:
        raise safe_error(404, "briefing_not_found", "No briefing available.")
    return fallback.content


@router.get("/runs/{run_id}/ai-briefing", response_class=PlainTextResponse)
def get_run_ai_briefing(run_id: str, session: Session = Depends(get_db_session)) -> str:
    if session.get(RunRow, run_id) is None:
        raise safe_error(404, "run_not_found", "Run not found.")
    content = _artifact_text(session, run_id, "ai_briefing")
    if content is None:
        content = _artifact_text(session, run_id, "daily_briefing")
    if content is None:
        raise safe_error(404, "artifact_not_found", "Run AI briefing artifact not found.")
    return content


def _request_id(http_request: Request) -> str | None:
    rid = getattr(http_request.state, "request_id", None)
    if isinstance(rid, str) and rid.strip():
        return rid.strip()
    return None


@router.post("/ask")
def ask(
    payload: AskRequest,
    http_request: Request,
    session: Session = Depends(get_db_session),
) -> dict[str, str]:
    records = _latest_triage_records(session)
    answer = answer_question(
        question=payload.question,
        assistant_name=payload.assistant_name,
        triage_records=records,
        session=session,
        request_id=_request_id(http_request),
    )
    return {"answer": answer}


@router.post("/evening-summary")
def evening_summary(
    payload: EveningSummaryRequest,
    http_request: Request,
    session: Session = Depends(get_db_session),
) -> dict[str, str]:
    records = _latest_triage_records(session)
    summary = generate_evening_summary(
        assistant_name=payload.assistant_name,
        triage_records=records,
        session=session,
        request_id=_request_id(http_request),
    )
    return {"summary": summary}


@router.post("/insights")
def insights(
    payload: InsightsRequest,
    http_request: Request,
    session: Session = Depends(get_db_session),
) -> dict[str, object]:
    records = _latest_triage_records(session)
    return generate_insights(
        assistant_name=payload.assistant_name,
        triage_records=records,
        session=session,
        request_id=_request_id(http_request),
    )


@router.get("/inputs")
def get_inputs() -> dict[str, object]:
    if not RAW_INPUT_DIR.exists():
        return {"files": []}
    files = sorted(p.name for p in RAW_INPUT_DIR.iterdir() if p.is_file() and p.suffix == ".json")
    return {"files": files}


@router.get("/capabilities")
def list_capabilities(session: Session = Depends(get_db_session)) -> list[Any]:
    from dataclasses import asdict, replace

    from opspilot.capabilities.registry import CapabilityStatus
    from opspilot.persistence.repositories import oauth_credentials

    connected = oauth_credentials.is_connected(session, provider="google")
    caps = []
    for cap in get_all_capabilities():
        if cap.id in {"email", "calendar"}:
            status = CapabilityStatus.CONNECTED if connected else CapabilityStatus.AVAILABLE
            caps.append(asdict(replace(cap, status=status)))
        else:
            caps.append(asdict(cap))
    return caps


@router.get("/capabilities/{capability_id}")
def get_capability_by_id(capability_id: str, session: Session = Depends(get_db_session)) -> Any:
    from dataclasses import asdict, replace

    from opspilot.capabilities.registry import CapabilityStatus
    from opspilot.persistence.repositories import oauth_credentials

    capability = get_capability(capability_id)
    if capability is None:
        raise safe_error(404, "capability_not_found", "Capability not found.")
    if capability.id in {"email", "calendar"}:
        connected = oauth_credentials.is_connected(session, provider="google")
        status = CapabilityStatus.CONNECTED if connected else CapabilityStatus.AVAILABLE
        return asdict(replace(capability, status=status))
    return asdict(capability)


@router.get("/calendar/week", response_class=JSONResponse)
def get_calendar_week(
    start: str,
    end: str,
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    from datetime import datetime

    from opspilot.persistence.repositories import meetings

    try:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
    except ValueError as exc:
        raise safe_error(400, "invalid_date_range", "start and end must be ISO datetimes.") from exc
    if start_dt.tzinfo is None or end_dt.tzinfo is None:
        raise safe_error(400, "invalid_date_range", "start and end must be timezone-aware.")
    rows = meetings.list_in_range(session, start=start_dt, end=end_dt)
    return {
        "meetings": [
            {
                "id": row.id,
                "provider_id": row.provider_id,
                "title": row.title,
                "start_at": row.start_at.isoformat(),
                "end_at": row.end_at.isoformat(),
            }
            for row in rows
        ]
    }
