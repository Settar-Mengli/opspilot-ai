"""Tests for triage_overlay service (B6 C6)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from opspilot.persistence.models import (
    RunRow,
    TriageDecisionRow,
    WorkItemRow,
)
from opspilot.persistence.repositories import triage_corrections
from opspilot.services.triage_overlay import latest_triage_with_overlay, promotion_hook


def _seed_work_item(session: Session, *, wid: str = "wi_overlay_1", source: str = "gmail") -> WorkItemRow:
    row = WorkItemRow(
        id=wid,
        source_type=source,
        subject_or_title="Test Item",
        body_or_description="Body",
        sender_or_requester="test@example.com",
        received_at=datetime(2026, 10, 1, 12, 0, tzinfo=UTC),
        tags=[],
    )
    session.add(row)
    session.flush()
    return row


def _seed_decision(
    session: Session,
    *,
    wid: str = "wi_overlay_1",
    run_id: str = "run_overlay_1",
) -> TriageDecisionRow:
    if session.get(RunRow, run_id) is None:
        session.add(RunRow(run_id=run_id, status="success"))
        session.flush()
    row = TriageDecisionRow(
        work_item_id=wid,
        run_id=run_id,
        urgency="low",
        urgency_reason="auto-classified low",
        category="info",
        category_reason="informational",
        sentiment="neutral",
        sentiment_reason="neutral tone",
    )
    session.add(row)
    session.flush()
    return row


def test_overlay_no_correction(db_session: Session) -> None:
    """Without a correction, the overlay returns decision labels verbatim."""
    _seed_work_item(db_session)
    _seed_decision(db_session)

    records = latest_triage_with_overlay(db_session)
    assert len(records) == 1
    rec = records[0]
    assert rec["urgency"] == "low"
    assert rec["category"] == "info"
    assert rec["sentiment"] == "neutral"
    assert rec["corrected"] is False


def test_overlay_with_correction(db_session: Session) -> None:
    """Correction labels override decision labels; reasons stay from decision."""
    _seed_work_item(db_session)
    _seed_decision(db_session)
    triage_corrections.upsert_correction(
        db_session,
        work_item_id="wi_overlay_1",
        urgency="high",
        category="action",
        sentiment="negative",
    )

    records = latest_triage_with_overlay(db_session)
    assert len(records) == 1
    rec = records[0]
    assert rec["urgency"] == "high"
    assert rec["category"] == "action"
    assert rec["sentiment"] == "negative"
    assert rec["urgency_reason"] == "auto-classified low"
    assert rec["corrected"] is True


def test_overlay_gmail_only_filter(db_session: Session) -> None:
    """gmail_only=True excludes non-gmail items."""
    _seed_work_item(db_session, wid="wi_gmail", source="gmail")
    _seed_decision(db_session, wid="wi_gmail", run_id="run_g")
    _seed_work_item(db_session, wid="wi_other", source="sample")
    _seed_decision(db_session, wid="wi_other", run_id="run_o")

    all_records = latest_triage_with_overlay(db_session, gmail_only=False)
    gmail_records = latest_triage_with_overlay(db_session, gmail_only=True)

    assert len(all_records) == 2
    assert len(gmail_records) == 1
    assert gmail_records[0]["id"] == "wi_gmail"


def test_drain_preserves_correction_overlay(db_session: Session) -> None:
    """A correction on item A persists through a second triage run on item B.

    After draining a new item, the overlay still returns the corrected
    labels for the previously corrected item.
    """
    _seed_work_item(db_session, wid="wi_a")
    _seed_decision(db_session, wid="wi_a", run_id="run1")
    triage_corrections.upsert_correction(
        db_session, work_item_id="wi_a", urgency="high", category="action", sentiment="positive"
    )

    _seed_work_item(db_session, wid="wi_b")
    _seed_decision(db_session, wid="wi_b", run_id="run2")

    records = latest_triage_with_overlay(db_session)
    by_id = {r["id"]: r for r in records}
    assert by_id["wi_a"]["corrected"] is True
    assert by_id["wi_a"]["urgency"] == "high"
    assert by_id["wi_b"]["corrected"] is False
    assert by_id["wi_b"]["urgency"] == "low"


def test_promotion_hook_returns_corrections(db_session: Session) -> None:
    """promotion_hook exports corrected items with original + corrected labels."""
    _seed_work_item(db_session)
    _seed_decision(db_session)
    triage_corrections.upsert_correction(
        db_session,
        work_item_id="wi_overlay_1",
        urgency="critical",
        category="escalation",
        sentiment="negative",
    )

    dataset = promotion_hook(db_session)
    assert len(dataset) == 1
    entry = dataset[0]
    assert entry["corrected_urgency"] == "critical"
    assert entry["original_urgency"] == "low"
    assert entry["subject_or_title"] == "Test Item"


def test_promotion_hook_empty_when_no_corrections(db_session: Session) -> None:
    _seed_work_item(db_session)
    _seed_decision(db_session)
    assert promotion_hook(db_session) == []
