"""/api/v1 route handlers (Postgres SoT)."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from opspilot.adapters.conversation_adapter import answer_question
from opspilot.adapters.evening_adapter import generate_evening_summary
from opspilot.adapters.insights_adapter import generate_insights
from opspilot.api.deps import get_db_session
from opspilot.api.paths import API_OUTPUT_DIR, RAW_INPUT_DIR
from opspilot.api.schemas import (
    AskRequest,
    EveningSummaryRequest,
    InsightsRequest,
    RunPipelineRequest,
    safe_error,
    safe_history_metadata,
)
from opspilot.api.services.persist import load_triage_json, persist_pipeline_outputs
from opspilot.api.services.pipeline import execute_pipeline, history_dir_from_outputs
from opspilot.capabilities.registry import get_all_capabilities, get_capability
from opspilot.config.settings import ai_settings
from opspilot.persistence.models import RunArtifactRow, RunRow, TriageDecisionRow, WorkItemRow

router = APIRouter(prefix="/api/v1")


def _preview_api_key(api_key: str | None) -> str | None:
    if not api_key:
        return None
    return f"sk-••••{api_key[-4:]}"


def _settings_payload() -> dict[str, object]:
    return {
        "provider": ai_settings.provider,
        "model": ai_settings.model,
        "api_key_set": bool(ai_settings.api_key),
        "api_key_preview": _preview_api_key(ai_settings.api_key),
    }


@router.get("/health", response_class=PlainTextResponse)
def health() -> str:
    return "ok"


@router.get("/settings", response_class=JSONResponse)
def get_settings() -> dict[str, object]:
    return _settings_payload()


@router.post("/runs")
async def create_run(
    req: RunPipelineRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    outputs = execute_pipeline(req)
    run_dir = history_dir_from_outputs(outputs)
    sample = RAW_INPUT_DIR / Path(req.input_file).name
    run_id = await persist_pipeline_outputs(session, run_dir=run_dir, sample_input=sample)
    lines = ["OpsPilot AI run completed."]
    for name, path in outputs.items():
        if name in {"run_id", "history_dir"}:
            continue
        lines.append(f"{name}: {path}")
    return {"status": "success", "stdout": "\n".join(lines), "run_id": run_id}


@router.get("/runs", response_class=JSONResponse)
async def list_runs(session: AsyncSession = Depends(get_db_session)) -> list[dict]:
    result = await session.execute(select(RunRow).order_by(desc(RunRow.finished_at), desc(RunRow.run_id)))
    rows = result.scalars().all()
    return [safe_history_metadata(dict(row.metadata_json or {"run_id": row.run_id})) for row in rows]


@router.get("/runs/{run_id}", response_class=JSONResponse)
async def get_run(run_id: str, session: AsyncSession = Depends(get_db_session)) -> dict:
    row = await session.get(RunRow, run_id)
    if row is None:
        raise safe_error(404, "run_not_found", "Run not found.")
    return safe_history_metadata(dict(row.metadata_json or {"run_id": row.run_id}))


@router.get("/triage", response_class=JSONResponse)
async def get_triage(session: AsyncSession = Depends(get_db_session)) -> list[dict]:
    """Latest triage decisions with AI-05 lite subject_or_title from WorkItem."""
    result = await session.execute(
        select(TriageDecisionRow, WorkItemRow)
        .join(WorkItemRow, TriageDecisionRow.work_item_id == WorkItemRow.id)
        .order_by(desc(TriageDecisionRow.id))
    )
    seen: set[str] = set()
    payload: list[dict] = []
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


async def _artifact_text(session: AsyncSession, run_id: str, logical_name: str) -> str | None:
    result = await session.execute(
        select(RunArtifactRow).where(
            RunArtifactRow.run_id == run_id,
            RunArtifactRow.name == logical_name,
        )
    )
    row = result.scalar_one_or_none()
    return None if row is None else row.content


@router.get("/runs/{run_id}/triage", response_class=JSONResponse)
async def get_run_triage(run_id: str, session: AsyncSession = Depends(get_db_session)) -> list:
    if await session.get(RunRow, run_id) is None:
        raise safe_error(404, "run_not_found", "Run not found.")
    content = await _artifact_text(session, run_id, "triage_results")
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
async def get_briefing(session: AsyncSession = Depends(get_db_session)) -> str:
    result = await session.execute(
        select(RunArtifactRow)
        .where(RunArtifactRow.name == "daily_briefing")
        .order_by(desc(RunArtifactRow.id))
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is not None:
        return row.content
    path = API_OUTPUT_DIR / "daily_briefing.txt"
    if path.is_file():
        return path.read_text(encoding="utf-8")
    raise safe_error(404, "briefing_not_found", "Briefing not found.")


@router.get("/runs/{run_id}/briefing", response_class=PlainTextResponse)
async def get_run_briefing(run_id: str, session: AsyncSession = Depends(get_db_session)) -> str:
    if await session.get(RunRow, run_id) is None:
        raise safe_error(404, "run_not_found", "Run not found.")
    content = await _artifact_text(session, run_id, "daily_briefing")
    if content is None:
        raise safe_error(404, "artifact_not_found", "Run briefing artifact not found.")
    return content


@router.get("/ai-briefing", response_class=PlainTextResponse)
def get_ai_briefing() -> str:
    ai_path = API_OUTPUT_DIR / "ai_briefing.txt"
    if ai_path.is_file():
        return ai_path.read_text(encoding="utf-8")
    fallback = API_OUTPUT_DIR / "daily_briefing.txt"
    if fallback.is_file():
        return fallback.read_text(encoding="utf-8")
    raise safe_error(404, "briefing_not_found", "No briefing available.")


@router.get("/runs/{run_id}/ai-briefing", response_class=PlainTextResponse)
async def get_run_ai_briefing(run_id: str, session: AsyncSession = Depends(get_db_session)) -> str:
    if await session.get(RunRow, run_id) is None:
        raise safe_error(404, "run_not_found", "Run not found.")
    content = await _artifact_text(session, run_id, "ai_briefing")
    if content is None:
        content = await _artifact_text(session, run_id, "daily_briefing")
    if content is None:
        raise safe_error(404, "artifact_not_found", "Run AI briefing artifact not found.")
    return content


@router.post("/ask")
def ask(payload: AskRequest) -> dict[str, str]:
    records = load_triage_json(API_OUTPUT_DIR / "triage_results.json")
    answer = answer_question(
        question=payload.question,
        assistant_name=payload.assistant_name,
        triage_records=records,
    )
    return {"answer": answer}


@router.post("/evening-summary")
def evening_summary(payload: EveningSummaryRequest) -> dict[str, str]:
    records = load_triage_json(API_OUTPUT_DIR / "triage_results.json")
    summary = generate_evening_summary(
        assistant_name=payload.assistant_name,
        triage_records=records,
    )
    return {"summary": summary}


@router.post("/insights")
def insights(payload: InsightsRequest) -> dict[str, object]:
    records = load_triage_json(API_OUTPUT_DIR / "triage_results.json")
    return generate_insights(
        assistant_name=payload.assistant_name,
        triage_records=records,
    )


@router.get("/inputs")
def get_inputs() -> dict[str, object]:
    if not RAW_INPUT_DIR.exists():
        return {"files": []}
    files = sorted(p.name for p in RAW_INPUT_DIR.iterdir() if p.is_file() and p.suffix == ".json")
    return {"files": files}


@router.get("/capabilities")
def list_capabilities() -> list[dict]:
    return get_all_capabilities()


@router.get("/capabilities/{capability_id}")
def get_capability_by_id(capability_id: str) -> dict:
    capability = get_capability(capability_id)
    if capability is None:
        raise safe_error(404, "capability_not_found", "Capability not found.")
    return capability
