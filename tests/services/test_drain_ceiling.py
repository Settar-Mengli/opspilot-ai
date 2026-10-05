"""Drain ceiling tests: ceiling_hit still generates a briefing."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from sqlalchemy.orm import Session

from opspilot.persistence.repositories.ops_jobs import insert_ops_job
from opspilot.persistence.repositories.work_items import upsert_by_provider_id
from opspilot.services.drain import drain
from opspilot.services.ops_jobs import claim_lease_idle


def _seed_gmail(session: Session, *, count: int = 3) -> list[str]:
    ids = []
    for i in range(count):
        wid = upsert_by_provider_id(
            session,
            provider_id=f"msg_{i}",
            source_type="gmail",
            subject_or_title=f"Subject {i}",
            body_or_description=f"Body of email {i}",
            sender_or_requester=f"user{i}@example.com",
            received_at=datetime(2026, 10, 3, 8, i, tzinfo=UTC),
        )
        ids.append(wid)
    session.flush()
    return ids


def test_ceiling_hit_still_briefs(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """When drain hits the ceiling, it still generates a briefing."""
    monkeypatch.setenv("OPSPILOT_BRIEF_REQUEST_RESERVE", "0")
    _seed_gmail(db_session, count=5)

    job = insert_ops_job(
        db_session,
        job_kind="morning",
        day_utc=date(2026, 10, 3),
        request_ceiling=60,
    )
    gen = claim_lease_idle(db_session, job.id)
    assert gen is not None
    db_session.commit()

    # Refresh job after commit.
    db_session.expire_all()
    job = db_session.get(type(job), job.id)
    assert job is not None

    # Drain with ceiling=2, reserve=0 → drain_limit=2, so only 2 items triaged.
    result = drain(
        db_session,
        job=job,
        generation=gen,
        ceiling=2,
        heartbeat_interval_s=9999,  # skip heartbeats in test
    )
    db_session.commit()

    assert result.triaged == 2
    assert result.ceiling_hit is True
    assert result.run_id is not None
    # Briefing should still be produced.
    assert result.briefing_text is not None
    assert len(result.briefing_text) > 0
    assert "OpsPilot" in result.briefing_text
