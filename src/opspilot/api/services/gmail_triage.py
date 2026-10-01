"""Triage Google-synced gmail work items already in Postgres."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from opspilot.api.schemas import RunPipelineRequest
from opspilot.api.services.persist import persist_pipeline_result
from opspilot.api.services.pipeline import execute_pipeline
from opspilot.persistence.repositories import work_items


def triage_connected_gmail(session: Session, *, run_date: date | None = None) -> dict[str, Any]:
    """Run pipeline on DB gmail rows; skip sample import. Returns run_id and triage count."""
    raw = work_items.list_gmail_raw(session)
    req = RunPipelineRequest(date=run_date or date.today())
    result = execute_pipeline(req, raw_items=raw)
    run_id = persist_pipeline_result(session, result, sample_input=None)
    return {
        "run_id": run_id,
        "triaged": int(result.metadata.get("triage_count") or len(result.work_items)),
    }
