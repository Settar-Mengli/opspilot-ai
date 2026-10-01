"""Meeting repository for WeekPanel."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from opspilot.persistence.models import MeetingRow


def new_meeting_id() -> str:
    return f"mtg_{uuid4().hex}"


def upsert_by_provider_id(
    session: Session,
    *,
    provider_id: str,
    title: str,
    start_at: datetime,
    end_at: datetime,
    updated_at: datetime | None = None,
) -> str:
    now = updated_at or datetime.now(UTC)
    existing = session.scalars(select(MeetingRow).where(MeetingRow.provider_id == provider_id)).one_or_none()
    if existing is not None:
        existing.title = title
        existing.start_at = start_at
        existing.end_at = end_at
        existing.updated_at = now
        session.flush()
        return existing.id

    row_id = new_meeting_id()
    stmt = pg_insert(MeetingRow).values(
        id=row_id,
        provider_id=provider_id,
        title=title,
        start_at=start_at,
        end_at=end_at,
        updated_at=now,
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_meetings_provider_id",
        set_={
            "title": stmt.excluded.title,
            "start_at": stmt.excluded.start_at,
            "end_at": stmt.excluded.end_at,
            "updated_at": stmt.excluded.updated_at,
        },
    )
    session.execute(stmt)
    session.flush()
    row = session.scalars(select(MeetingRow).where(MeetingRow.provider_id == provider_id)).one()
    return row.id


def list_in_range(session: Session, *, start: datetime, end: datetime) -> list[MeetingRow]:
    stmt = (
        select(MeetingRow)
        .where(MeetingRow.start_at < end)
        .where(MeetingRow.end_at > start)
        .order_by(MeetingRow.start_at.asc())
    )
    return list(session.scalars(stmt).all())


def delete_by_provider_id(session: Session, *, provider_id: str) -> bool:
    """Delete a meeting by Google event id. Returns True if a row was deleted."""
    row = session.scalars(select(MeetingRow).where(MeetingRow.provider_id == provider_id)).one_or_none()
    if row is None:
        return False
    session.delete(row)
    session.flush()
    return True
