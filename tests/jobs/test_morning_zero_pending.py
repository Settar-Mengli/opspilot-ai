"""Zero pending true no-op via end-to-end run_morning."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from opspilot.persistence.models import OpsJobLeaseRow, OpsJobRow, RunArtifactRow, RunRow
from opspilot.persistence.repositories.work_items import count_gmail_untriaged


def test_run_morning_zero_pending_true_noop(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """E2E: pending=0, no gmail run / no corrections → succeeded, no run_id, lease released."""
    monkeypatch.setattr("opspilot.jobs.morning_run._preflight", lambda: None)
    monkeypatch.setenv("OPSPILOT_DEMO_MODE", "1")
    monkeypatch.delenv("OPSPILOT_SIMULATE_GOOGLE_REAUTH", raising=False)
    monkeypatch.setattr("opspilot.jobs.morning_run.notify_morning_outcome", lambda *a, **k: None)

    assert count_gmail_untriaged(db_session) == 0
    db_session.commit()

    from opspilot.jobs.morning_run import run_morning

    assert run_morning(force_override=True) == 0
    db_session.expire_all()

    job = db_session.scalars(select(OpsJobRow).order_by(OpsJobRow.created_at.desc())).first()
    assert job is not None
    assert job.status == "succeeded"
    assert job.triaged == 0
    assert job.run_id is None
    assert (job.metadata_json or {}).get("brief_reason") != "corrections_only"

    lease = db_session.get(OpsJobLeaseRow, 1)
    assert lease is not None
    assert lease.job_id is None

    run_count = db_session.scalar(select(func.count()).select_from(RunRow))
    assert run_count == 0
    artifact_count = db_session.scalar(select(func.count()).select_from(RunArtifactRow))
    assert artifact_count == 0


def test_zero_pending_helper_branch_no_run_no_brief(db_session: Session) -> None:
    """Low-level: simulated no-op finalize leaves no runs/artifacts (regression)."""
    from datetime import date

    from opspilot.persistence.repositories.ops_jobs import update_ops_job_fields
    from opspilot.services.ops_jobs import claim_lease_idle, day_claim_morning, release_lease

    job = day_claim_morning(db_session, day_utc=date(2026, 10, 3))
    assert job is not None
    gen = claim_lease_idle(db_session, job.id)
    assert gen is not None
    db_session.commit()
    db_session.expire_all()
    job = db_session.get(OpsJobRow, job.id)
    assert job is not None

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
    assert job.run_id is None

    run_count = db_session.scalar(select(func.count()).select_from(RunRow))
    assert run_count == 0
    artifact_count = db_session.scalar(select(func.count()).select_from(RunArtifactRow))
    assert artifact_count == 0
