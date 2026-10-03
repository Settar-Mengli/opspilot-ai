"""Day claim tests: H5a noop after success; H5b force; H5c retry after failed."""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from opspilot.persistence.repositories.ops_jobs import update_ops_job_fields
from opspilot.services.ops_jobs import day_claim_morning


def test_h5a_noop_after_success(db_session: Session) -> None:
    """Second nonforce claim on the same day is blocked when first succeeded."""
    first = day_claim_morning(db_session, day_utc=date(2026, 10, 3))
    assert first is not None
    update_ops_job_fields(db_session, first, status="succeeded", finished_at=datetime.now(UTC))
    db_session.commit()

    second = day_claim_morning(db_session, day_utc=date(2026, 10, 3))
    assert second is None, "nonforce claim should be blocked after succeeded"


def test_h5b_force_after_success(db_session: Session) -> None:
    """Force claim succeeds even when same day already has a succeeded job."""
    first = day_claim_morning(db_session, day_utc=date(2026, 10, 3))
    assert first is not None
    update_ops_job_fields(db_session, first, status="succeeded", finished_at=datetime.now(UTC))
    db_session.commit()

    forced = day_claim_morning(db_session, day_utc=date(2026, 10, 3), force_override=True)
    assert forced is not None
    assert forced.force_override is True


def test_h5c_retry_after_failed(db_session: Session) -> None:
    """Nonforce claim succeeds after a failed job (failed not in conflict guard)."""
    first = day_claim_morning(db_session, day_utc=date(2026, 10, 3))
    assert first is not None
    update_ops_job_fields(db_session, first, status="failed", finished_at=datetime.now(UTC))
    db_session.commit()

    retry = day_claim_morning(db_session, day_utc=date(2026, 10, 3))
    # 'failed' is excluded from the partial unique index, so this should succeed.
    assert retry is not None
