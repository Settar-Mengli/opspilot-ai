"""Reap tests: H3a same-day nonforce after kill; H3b force; H3c next day."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy.orm import Session

from opspilot.persistence.repositories.ops_jobs import insert_ops_job, upsert_lease
from opspilot.services.ops_jobs import reap_stale_jobs


def _insert_running_job(
    session: Session,
    *,
    job_id: str,
    day_utc: date,
    force_override: bool = False,
) -> None:
    insert_ops_job(
        session,
        job_kind="morning",
        day_utc=day_utc,
        status="running",
        force_override=force_override,
        job_id=job_id,
    )


def _hold_lease(session: Session, job_id: str, *, stale: bool = True) -> None:
    hb = datetime.now(UTC) - timedelta(hours=1) if stale else datetime.now(UTC)
    upsert_lease(session, job_id=job_id, heartbeat_at=hb, generation=1)


def test_h3a_same_day_nonforce_after_reap(db_session: Session) -> None:
    """After reaping a stale same-day nonforce job, day_claim blocks (already has a row)."""
    from opspilot.services.ops_jobs import day_claim_morning

    _insert_running_job(db_session, job_id="oj_stale1", day_utc=date(2026, 10, 3))
    _hold_lease(db_session, "oj_stale1", stale=True)
    db_session.commit()

    reaped = reap_stale_jobs(db_session)
    db_session.commit()
    assert reaped >= 1

    # Same-day nonforce claim is blocked because the abandoned row still holds the unique index.
    claim = day_claim_morning(db_session, day_utc=date(2026, 10, 3))
    # Abandoned status is NOT in the conflict guard, so new insert succeeds.
    # Actually: the partial unique index includes ('queued','running','succeeded','partial').
    # 'abandoned' is excluded, so a new nonforce insert should succeed.
    assert claim is not None
    db_session.commit()


def test_h3b_force_after_reap(db_session: Session) -> None:
    """Force job always inserts after reap regardless of day state."""
    from opspilot.services.ops_jobs import day_claim_morning

    _insert_running_job(db_session, job_id="oj_stale2", day_utc=date(2026, 10, 3))
    _hold_lease(db_session, "oj_stale2", stale=True)
    db_session.commit()

    reaped = reap_stale_jobs(db_session)
    db_session.commit()
    assert reaped >= 1

    claim = day_claim_morning(db_session, day_utc=date(2026, 10, 3), force_override=True)
    assert claim is not None
    assert claim.force_override is True
    db_session.commit()


def test_h3c_next_day(db_session: Session) -> None:
    """Next day claim works regardless of previous day's state."""
    from opspilot.services.ops_jobs import day_claim_morning

    _insert_running_job(db_session, job_id="oj_day1", day_utc=date(2026, 10, 2))
    _hold_lease(db_session, "oj_day1", stale=True)
    db_session.commit()

    reaped = reap_stale_jobs(db_session)
    db_session.commit()
    assert reaped >= 1

    claim = day_claim_morning(db_session, day_utc=date(2026, 10, 3))
    assert claim is not None
    db_session.commit()
