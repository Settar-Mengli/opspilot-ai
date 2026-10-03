"""Corrections-only: brief updates an existing gmail-linked run."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from opspilot.persistence.models import (
    RunArtifactRow,
    RunRow,
    TriageDecisionRow,
)
from opspilot.persistence.repositories.work_items import count_gmail_untriaged, upsert_by_provider_id


def _seed_triaged_gmail_item(session: Session, *, run_id: str, idx: int = 0) -> str:
    """Insert a gmail work item with a triage decision on it."""
    wid = upsert_by_provider_id(
        session,
        provider_id=f"msg_corr_{idx}",
        source_type="gmail",
        subject_or_title=f"Corr test {idx}",
        body_or_description=f"Body {idx}",
        sender_or_requester=f"corr{idx}@example.com",
        received_at=datetime(2026, 10, 2, 9, idx, tzinfo=UTC),
    )

    session.add(
        TriageDecisionRow(
            work_item_id=wid,
            run_id=run_id,
            urgency="medium",
            urgency_reason="test",
            category="task",
            category_reason="test",
            sentiment="neutral",
            sentiment_reason="test",
            confidence=0.9,
            evidence_refs=[wid],
        )
    )
    session.flush()
    return wid


def test_corrections_only_upserts_brief_on_existing_run(db_session: Session) -> None:
    """When pending=0 but a gmail run exists, brief is regenerated (corrections-only)."""
    # Create a pre-existing run with gmail triage decisions.
    run_id = "run-20261002-090000-000"
    db_session.add(RunRow(run_id=run_id, started_at=datetime(2026, 10, 2, 9, tzinfo=UTC), status="success"))
    db_session.flush()

    _seed_triaged_gmail_item(db_session, run_id=run_id, idx=0)
    _seed_triaged_gmail_item(db_session, run_id=run_id, idx=1)
    db_session.commit()

    # No untriaged items.
    assert count_gmail_untriaged(db_session) == 0

    # Exercise _upsert_corrections_brief.
    from opspilot.jobs.morning_run import _latest_gmail_run_id, _upsert_corrections_brief

    found_run = _latest_gmail_run_id(db_session)
    assert found_run == run_id

    briefing = _upsert_corrections_brief(db_session, run_id)
    db_session.commit()

    assert briefing is not None
    assert len(briefing) > 0

    # Artifact is on the existing run.
    artifact = db_session.scalars(
        select(RunArtifactRow).where(RunArtifactRow.run_id == run_id, RunArtifactRow.name == "daily_briefing")
    ).one()
    assert artifact.content == briefing


def test_corrections_only_upserts_overwrites_existing_brief(db_session: Session) -> None:
    """When a brief already exists on the run, corrections-only overwrites it."""
    run_id = "run-20261002-100000-000"
    db_session.add(RunRow(run_id=run_id, started_at=datetime(2026, 10, 2, 10, tzinfo=UTC), status="success"))
    db_session.add(RunArtifactRow(run_id=run_id, name="daily_briefing", content_type="text", content="old brief"))
    db_session.flush()

    _seed_triaged_gmail_item(db_session, run_id=run_id, idx=5)
    db_session.commit()

    from opspilot.jobs.morning_run import _upsert_corrections_brief

    briefing = _upsert_corrections_brief(db_session, run_id)
    db_session.commit()

    assert briefing is not None
    assert briefing != "old brief"

    artifacts = db_session.scalars(
        select(RunArtifactRow).where(RunArtifactRow.run_id == run_id, RunArtifactRow.name == "daily_briefing")
    ).all()
    assert len(artifacts) == 1
    assert artifacts[0].content == briefing
