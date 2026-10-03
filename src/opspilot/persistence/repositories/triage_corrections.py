"""Triage correction overlay repository (B6)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from opspilot.persistence.models import TriageCorrectionRow


def get_correction(session: Session, work_item_id: str) -> TriageCorrectionRow | None:
    return session.get(TriageCorrectionRow, work_item_id)


def upsert_correction(
    session: Session,
    *,
    work_item_id: str,
    urgency: str,
    category: str,
    sentiment: str,
) -> TriageCorrectionRow:
    now = datetime.now(UTC)
    stmt = pg_insert(TriageCorrectionRow).values(
        work_item_id=work_item_id,
        urgency=urgency,
        category=category,
        sentiment=sentiment,
        created_at=now,
        updated_at=now,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["work_item_id"],
        set_={
            "urgency": stmt.excluded.urgency,
            "category": stmt.excluded.category,
            "sentiment": stmt.excluded.sentiment,
            "updated_at": stmt.excluded.updated_at,
        },
    )
    session.execute(stmt)
    session.flush()
    row = session.get(TriageCorrectionRow, work_item_id)
    assert row is not None
    return row


def delete_correction(session: Session, work_item_id: str) -> bool:
    row = session.get(TriageCorrectionRow, work_item_id)
    if row is None:
        return False
    session.delete(row)
    session.flush()
    return True
