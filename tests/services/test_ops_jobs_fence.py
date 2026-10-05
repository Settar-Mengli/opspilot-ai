"""Fence / heartbeat / takeover tests for ops_jobs lease primitives."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from opspilot.persistence.repositories.ops_jobs import insert_ops_job
from opspilot.services.ops_jobs import (
    FenceError,
    claim_lease_idle,
    fence_check,
    heartbeat,
    takeover_stale_lease,
)


@pytest.fixture
def _running_job(db_session: Session) -> tuple[str, int]:
    """Seed a morning job and claim the lease."""
    job = insert_ops_job(db_session, job_kind="morning", day_utc=date(2026, 10, 3), request_ceiling=60)
    gen = claim_lease_idle(db_session, job.id)
    assert gen is not None
    db_session.commit()
    return job.id, gen


def test_long_item_heartbeat_prevents_stale(db_session: Session, _running_job: tuple[str, int]) -> None:
    """A heartbeat refreshes the lease timestamp, preventing stale takeover."""
    job_id, gen = _running_job

    # Heartbeat succeeds.
    assert heartbeat(db_session, job_id, gen) is True
    db_session.commit()

    # Fence passes.
    fence_check(db_session, job_id, gen)

    # A second job tries takeover but lease is fresh → None.
    job2 = insert_ops_job(db_session, job_kind="sync_drain", day_utc=date(2026, 10, 3), request_ceiling=40)
    db_session.commit()
    result = takeover_stale_lease(db_session, job2.id, stale_s=900)
    assert result is None

    # Fence still passes for original.
    fence_check(db_session, job_id, gen)


def test_takeover_waits_until_persist_commits(db_session: Session, _running_job: tuple[str, int]) -> None:
    """Takeover only succeeds when heartbeat is stale (simulated by backdating)."""
    job_id, gen = _running_job

    # Backdate the heartbeat to make it stale.
    db_session.execute(
        text("UPDATE ops_job_lease SET heartbeat_at = :old WHERE slot = 1"),
        {"old": datetime.now(UTC) - timedelta(seconds=1000)},
    )
    db_session.commit()

    # New job can now take over.
    job2 = insert_ops_job(db_session, job_kind="sync_drain", day_utc=date(2026, 10, 3), request_ceiling=40)
    db_session.commit()

    gen2 = takeover_stale_lease(db_session, job2.id, stale_s=900)
    assert gen2 is not None
    assert gen2 > gen
    db_session.commit()

    # Original fence now fails.
    with pytest.raises(FenceError):
        fence_check(db_session, job_id, gen)

    # New holder's fence passes.
    fence_check(db_session, job2.id, gen2)
