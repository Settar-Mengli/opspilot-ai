"""Lease primitives: concurrent morning + sync → only one lease holder."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy.orm import Session

from opspilot.persistence.repositories.ops_jobs import insert_ops_job
from opspilot.services.ops_jobs import claim_lease_idle, release_lease


@pytest.fixture
def _morning_and_sync_jobs(db_session: Session) -> tuple[str, str]:
    """Seed a morning and a sync_drain job, both queued."""
    m = insert_ops_job(db_session, job_kind="morning", day_utc=date(2026, 10, 3), request_ceiling=60)
    s = insert_ops_job(db_session, job_kind="sync_drain", day_utc=date(2026, 10, 3), request_ceiling=40)
    db_session.commit()
    return m.id, s.id


def test_concurrent_morning_and_sync_one_lease(db_session: Session, _morning_and_sync_jobs: tuple[str, str]) -> None:
    """Only one job can hold the singleton lease at a time."""
    morning_id, sync_id = _morning_and_sync_jobs

    # Morning claims first.
    gen1 = claim_lease_idle(db_session, morning_id)
    db_session.commit()
    assert gen1 is not None
    assert gen1 >= 1

    # Sync tries to claim while morning holds → None.
    gen2 = claim_lease_idle(db_session, sync_id)
    assert gen2 is None

    # Morning releases.
    release_lease(db_session, morning_id, gen1)
    db_session.commit()

    # Now sync can claim.
    gen3 = claim_lease_idle(db_session, sync_id)
    db_session.commit()
    assert gen3 is not None
    assert gen3 > gen1
