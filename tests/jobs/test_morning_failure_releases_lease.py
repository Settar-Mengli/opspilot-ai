"""H2: mid-run failure marks job failed and releases lease; notify must not mask."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from opspilot.persistence.models import OpsJobLeaseRow, OpsJobRow


def _hermetic_morning(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("opspilot.jobs.morning_run._preflight", lambda: None)
    monkeypatch.setenv("OPSPILOT_DEMO_MODE", "0")
    monkeypatch.delenv("OPSPILOT_SIMULATE_GOOGLE_REAUTH", raising=False)


def test_crash_mid_run_releases_lease_and_marks_failed(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """Exception after lease acquired → failed job, lease free, original error raised."""
    _hermetic_morning(monkeypatch)
    notify_calls: list[tuple[str, str]] = []

    def _boom(*_a: object, **_k: object) -> dict[str, object]:
        raise RuntimeError("injected_sync_crash")

    def _notify(job_id: str, status: str, **_meta: object) -> None:
        notify_calls.append((job_id, status))

    monkeypatch.setattr("opspilot.services.google_sync.run_sync", _boom)
    monkeypatch.setattr("opspilot.jobs.morning_run.notify_morning_outcome", _notify)
    # Credential present so sync path is taken (not reauth skip).
    monkeypatch.setattr("opspilot.jobs.morning_run._google_credential_present", lambda _s: True)
    monkeypatch.setattr(
        "opspilot.services.operator_session.demo_mode_enabled",
        lambda: False,
    )
    db_session.commit()

    from opspilot.jobs.morning_run import run_morning

    with pytest.raises(RuntimeError, match="injected_sync_crash"):
        run_morning(force_override=True)

    db_session.expire_all()
    job = db_session.scalars(select(OpsJobRow).order_by(OpsJobRow.created_at.desc())).first()
    assert job is not None
    assert job.status == "failed"
    assert job.error_code == "morning_run_error"
    lease = db_session.get(OpsJobLeaseRow, 1)
    assert lease is not None
    assert lease.job_id is None
    assert notify_calls == [(job.id, "failed")]


def test_notify_failure_does_not_mask_original_or_skip_release(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Telegram raising during cleanup must not replace original or leave lease held."""
    _hermetic_morning(monkeypatch)

    def _boom(*_a: object, **_k: object) -> dict[str, object]:
        raise RuntimeError("injected_sync_crash")

    def _notify_raises(*_a: object, **_k: object) -> None:
        raise RuntimeError("telegram_cleanup_boom")

    monkeypatch.setattr("opspilot.services.google_sync.run_sync", _boom)
    monkeypatch.setattr("opspilot.jobs.morning_run.notify_morning_outcome", _notify_raises)
    monkeypatch.setattr("opspilot.jobs.morning_run._google_credential_present", lambda _s: True)
    monkeypatch.setattr(
        "opspilot.services.operator_session.demo_mode_enabled",
        lambda: False,
    )
    db_session.commit()

    from opspilot.jobs.morning_run import run_morning

    with pytest.raises(RuntimeError, match="injected_sync_crash") as excinfo:
        run_morning(force_override=True)
    assert "telegram_cleanup_boom" not in str(excinfo.value)

    db_session.expire_all()
    job = db_session.scalars(select(OpsJobRow).order_by(OpsJobRow.created_at.desc())).first()
    assert job is not None
    assert job.status == "failed"
    assert job.error_code == "morning_run_error"
    lease = db_session.get(OpsJobLeaseRow, 1)
    assert lease is not None
    assert lease.job_id is None
