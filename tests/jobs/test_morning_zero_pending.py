"""Zero pending: no run row, no brief, job succeeded with triaged=0."""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from opspilot.persistence.models import OpsJobRow, RunArtifactRow, RunRow
from opspilot.persistence.repositories.ops_jobs import update_ops_job_fields
from opspilot.persistence.repositories.work_items import count_gmail_untriaged
from opspilot.services.ops_jobs import claim_lease_idle, day_claim_morning, release_lease


def test_zero_pending_no_run_no_brief(db_session: Session) -> None:
    """When count_gmail_untriaged=0 and no corrections, job succeeds with no run/brief."""
    # No work items seeded → pending = 0.
    assert count_gmail_untriaged(db_session) == 0

    job = day_claim_morning(db_session, day_utc=date(2026, 10, 3))
    assert job is not None
    gen = claim_lease_idle(db_session, job.id)
    assert gen is not None
    db_session.commit()
    db_session.expire_all()
    job = db_session.get(OpsJobRow, job.id)
    assert job is not None

    pending = count_gmail_untriaged(db_session)
    assert pending == 0

    # Simulate zero-pending branch: succeed with triaged=0.
    update_ops_job_fields(
        db_session,
        job,
        status="succeeded",
        triaged=0,
        finished_at=datetime.now(UTC),
    )
    release_lease(db_session, job.id, gen)
    db_session.commit()

    db_session.expire_all()
    job = db_session.get(OpsJobRow, job.id)
    assert job is not None
    assert job.status == "succeeded"
    assert job.triaged == 0

    # No run rows or artifacts created.
    run_count = db_session.scalar(select(func.count()).select_from(RunRow))
    assert run_count == 0
    artifact_count = db_session.scalar(select(func.count()).select_from(RunArtifactRow))
    assert artifact_count == 0
