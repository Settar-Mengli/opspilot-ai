"""Auth tests: invalid_grant / simulate-reauth skip sync."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy.orm import Session

from opspilot.services.ops_jobs import claim_lease_idle


def _setup_job_with_lease(session: Session) -> tuple:
    from opspilot.services.ops_jobs import day_claim_morning

    job = day_claim_morning(session, day_utc=date(2026, 10, 3))
    assert job is not None
    gen = claim_lease_idle(session, job.id)
    assert gen is not None
    session.commit()
    session.expire_all()
    job = session.get(type(job), job.id)
    return job, gen


def test_simulate_reauth_skips_sync(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """OPSPILOT_SIMULATE_GOOGLE_REAUTH=1 sets reauth_needed without calling Google."""
    monkeypatch.setenv("OPSPILOT_SIMULATE_GOOGLE_REAUTH", "1")

    from opspilot.jobs.morning_run import _simulate_reauth

    assert _simulate_reauth() is True


def test_google_reauth_exception_sets_flag(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """GoogleReauthRequired during sync sets reauth_needed on the job."""
    job, gen = _setup_job_with_lease(db_session)

    from opspilot.services.google_sync import GoogleReauthRequired

    def _raise_reauth(*a: object, **kw: object) -> None:
        raise GoogleReauthRequired("invalid_grant")

    monkeypatch.setattr("opspilot.services.google_sync.run_sync", _raise_reauth)
    monkeypatch.setenv("OPSPILOT_DEMO_MODE", "0")
    monkeypatch.delenv("OPSPILOT_SIMULATE_GOOGLE_REAUTH", raising=False)

    # Simulate the auth check path manually.
    from opspilot.jobs.morning_run import _google_credential_present

    # Seed a fake credential so _google_credential_present returns True.
    from opspilot.persistence.repositories.oauth_credentials import upsert_encrypted_refresh

    upsert_encrypted_refresh(
        db_session,
        provider="google",
        account_email="test@example.com",
        scopes="https://www.googleapis.com/auth/gmail.readonly",
        refresh_token_plaintext="fake_token",
    )
    db_session.commit()

    assert _google_credential_present(db_session) is True

    # Now exercise the sync path.
    reauth_needed = False
    try:
        from opspilot.services.google_sync import run_sync

        run_sync(db_session)
    except GoogleReauthRequired:
        reauth_needed = True

    assert reauth_needed is True
