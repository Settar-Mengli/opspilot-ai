"""Work item repository (provider_id upsert for Gmail sync)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import exists, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from opspilot.persistence.models import TriageDecisionRow, WorkItemRow


def new_work_item_id() -> str:
    return f"wi_{uuid4().hex}"


def upsert_by_provider_id(
    session: Session,
    *,
    provider_id: str,
    source_type: str,
    subject_or_title: str,
    body_or_description: str,
    sender_or_requester: str,
    received_at: datetime,
    thread_id: str | None = None,
    tags: list[Any] | None = None,
) -> str:
    """Insert or update a work item keyed by unique provider_id. Returns row id."""
    if not provider_id:
        raise ValueError("provider_id required")
    existing = session.scalars(select(WorkItemRow).where(WorkItemRow.provider_id == provider_id)).one_or_none()
    if existing is not None:
        existing.source_type = source_type
        existing.subject_or_title = subject_or_title
        existing.body_or_description = body_or_description
        existing.sender_or_requester = sender_or_requester
        existing.received_at = received_at
        existing.thread_id = thread_id
        if tags is not None:
            existing.tags = tags
        session.flush()
        return existing.id

    row_id = new_work_item_id()
    stmt = pg_insert(WorkItemRow).values(
        id=row_id,
        provider_id=provider_id,
        source_type=source_type,
        subject_or_title=subject_or_title,
        body_or_description=body_or_description,
        sender_or_requester=sender_or_requester,
        received_at=received_at,
        thread_id=thread_id,
        tags=tags or [],
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_work_items_provider_id",
        set_={
            "source_type": stmt.excluded.source_type,
            "subject_or_title": stmt.excluded.subject_or_title,
            "body_or_description": stmt.excluded.body_or_description,
            "sender_or_requester": stmt.excluded.sender_or_requester,
            "received_at": stmt.excluded.received_at,
            "thread_id": stmt.excluded.thread_id,
            "tags": stmt.excluded.tags,
        },
    )
    session.execute(stmt)
    session.flush()
    row = session.scalars(select(WorkItemRow).where(WorkItemRow.provider_id == provider_id)).one()
    return row.id


def delete_by_provider_id(session: Session, *, provider_id: str) -> bool:
    """Delete a work item by Gmail message id. Returns True if a row was deleted."""
    row = session.scalars(select(WorkItemRow).where(WorkItemRow.provider_id == provider_id)).one_or_none()
    if row is None:
        return False
    session.delete(row)
    session.flush()
    return True


def _gmail_untriaged_filter() -> Any:
    has_decision = exists(select(TriageDecisionRow.id).where(TriageDecisionRow.work_item_id == WorkItemRow.id))
    return (WorkItemRow.source_type == "gmail") & (~has_decision)


def count_gmail_untriaged(session: Session) -> int:
    """Count gmail work items with no triage_decisions row."""
    n = session.scalar(select(func.count()).select_from(WorkItemRow).where(_gmail_untriaged_filter()))
    return int(n or 0)


def list_gmail_untriaged_raw(session: Session, *, limit: int) -> list[dict[str, Any]]:
    """Gmail items without any triage decision, oldest first, capped."""
    if limit <= 0:
        return []
    rows = session.scalars(
        select(WorkItemRow)
        .where(_gmail_untriaged_filter())
        .order_by(WorkItemRow.received_at.asc(), WorkItemRow.id.asc())
        .limit(limit)
    ).all()
    return [_row_to_raw(row) for row in rows]


def list_gmail_raw(session: Session) -> list[dict[str, Any]]:
    """Return gmail work items as ingest-shaped dicts (existing row ids preserved)."""
    rows = session.scalars(
        select(WorkItemRow).where(WorkItemRow.source_type == "gmail").order_by(WorkItemRow.received_at.desc())
    ).all()
    return [_row_to_raw(row) for row in rows]


def _row_to_raw(row: WorkItemRow) -> dict[str, Any]:
    received = row.received_at.isoformat() if hasattr(row.received_at, "isoformat") else str(row.received_at)
    return {
        "id": row.id,
        "source_type": "gmail",
        "subject_or_title": row.subject_or_title,
        "body_or_description": row.body_or_description,
        "sender_or_requester": row.sender_or_requester,
        "received_at": received,
        "tags": list(row.tags or []),
        "provider_id": row.provider_id,
    }
