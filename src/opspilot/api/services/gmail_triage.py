"""Triage Google-synced gmail work items already in Postgres."""

from __future__ import annotations

import logging
import os
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from opspilot.api.schemas import RunPipelineRequest
from opspilot.api.services.persist import persist_pipeline_result
from opspilot.api.services.pipeline import execute_pipeline
from opspilot.persistence.repositories import work_items

logger = logging.getLogger("opspilot.api.gmail_triage")

_DEFAULT_CAP = 10


def sync_triage_cap() -> int:
    """Max gmail items to triage per Sync / connected POST /runs (OPSPILOT_SYNC_TRIAGE_CAP)."""
    raw = os.environ.get("OPSPILOT_SYNC_TRIAGE_CAP", str(_DEFAULT_CAP)).strip()
    try:
        return max(0, int(raw))
    except ValueError:
        logger.warning("invalid OPSPILOT_SYNC_TRIAGE_CAP=%r; using %s", raw, _DEFAULT_CAP)
        return _DEFAULT_CAP


def triage_connected_gmail(
    session: Session,
    *,
    run_date: date | None = None,
) -> dict[str, Any]:
    """Triage untriaged gmail rows on ``session`` (caller owns commit), capped.

    Selects only gmail items with no ``triage_decisions`` row, oldest first.
    Returns run_id (nullable), triaged count, and pending remaining after this batch.
    """
    cap = sync_triage_cap()
    pending_before = work_items.count_gmail_untriaged(session)
    raw = work_items.list_gmail_untriaged_raw(session, limit=cap)
    if not raw:
        return {"run_id": None, "triaged": 0, "pending": pending_before}

    req = RunPipelineRequest(date=run_date or date.today())
    result = execute_pipeline(req, raw_items=raw)
    run_id = persist_pipeline_result(session, result, sample_input=None)
    triaged = int(result.metadata.get("triage_count") or len(result.work_items))
    pending = max(0, pending_before - triaged)
    return {
        "run_id": run_id,
        "triaged": triaged,
        "pending": pending,
    }


def triage_connected_gmail_fresh(*, run_date: date | None = None) -> dict[str, Any]:
    """Open a short-lived Session, triage a capped batch, commit (or roll back)."""
    from opspilot.api.deps import _get_factory

    factory = _get_factory()
    with factory() as session:
        try:
            out = triage_connected_gmail(session, run_date=run_date)
            session.commit()
            return out
        except Exception:
            try:
                session.rollback()
            except Exception:
                logger.exception("rollback_failed")
            raise
