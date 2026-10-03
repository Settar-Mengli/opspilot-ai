"""Tests for triage_corrections repository — cascade + CRUD (B6 C6)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from opspilot.persistence.models import TriageCorrectionRow, WorkItemRow
from opspilot.persistence.repositories import triage_corrections


def _seed_work_item(session: Session, wid: str = "wi_tc_1") -> WorkItemRow:
    row = WorkItemRow(
        id=wid,
        source_type="gmail",
        subject_or_title="Cascade test",
        body_or_description="Body",
        sender_or_requester="user@example.com",
        received_at=datetime(2026, 10, 1, 12, 0, tzinfo=UTC),
        tags=[],
    )
    session.add(row)
    session.flush()
    return row


def test_upsert_creates_correction(db_session: Session) -> None:
    _seed_work_item(db_session)
    row = triage_corrections.upsert_correction(
        db_session,
        work_item_id="wi_tc_1",
        urgency="high",
        category="action",
        sentiment="positive",
    )
    assert row.urgency == "high"
    assert row.category == "action"
    assert row.sentiment == "positive"


def test_upsert_updates_existing(db_session: Session) -> None:
    _seed_work_item(db_session)
    triage_corrections.upsert_correction(
        db_session, work_item_id="wi_tc_1", urgency="low", category="info", sentiment="neutral"
    )
    updated = triage_corrections.upsert_correction(
        db_session, work_item_id="wi_tc_1", urgency="high", category="action", sentiment="negative"
    )
    assert updated.urgency == "high"
    assert updated.category == "action"
    assert updated.sentiment == "negative"


def test_delete_correction(db_session: Session) -> None:
    _seed_work_item(db_session)
    triage_corrections.upsert_correction(
        db_session, work_item_id="wi_tc_1", urgency="high", category="action", sentiment="positive"
    )
    assert triage_corrections.delete_correction(db_session, "wi_tc_1") is True
    assert triage_corrections.get_correction(db_session, "wi_tc_1") is None


def test_delete_nonexistent_returns_false(db_session: Session) -> None:
    assert triage_corrections.delete_correction(db_session, "nonexistent") is False


def test_cascade_deletes_correction_with_work_item(db_session: Session) -> None:
    """Deleting the parent work_item cascades to triage_corrections."""
    _seed_work_item(db_session)
    triage_corrections.upsert_correction(
        db_session, work_item_id="wi_tc_1", urgency="high", category="action", sentiment="positive"
    )
    db_session.flush()

    assert db_session.get(TriageCorrectionRow, "wi_tc_1") is not None

    wi = db_session.get(WorkItemRow, "wi_tc_1")
    assert wi is not None
    from sqlalchemy import delete

    db_session.execute(delete(WorkItemRow).where(WorkItemRow.id == "wi_tc_1"))
    db_session.flush()

    assert db_session.get(TriageCorrectionRow, "wi_tc_1") is None
