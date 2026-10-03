"""Lifespan: abandon sync_drain on startup, leave morning alone (B6 C5)."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from opspilot.api.app import create_app
from opspilot.api.deps import reset_db_engine
from opspilot.persistence.models import OpsJobLeaseRow, OpsJobRow
from opspilot.persistence.repositories.ops_jobs import (
    LEASE_SLOT,
    insert_ops_job,
    upsert_lease,
)


def _setup_env(
    monkeypatch: pytest.MonkeyPatch,
    test_database_url: str,
) -> None:
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("OPSPILOT_SESSION_SECRET", "test-session-secret-not-real")
    monkeypatch.setenv("OPSPILOT_DEMO_MODE", "0")
    monkeypatch.setenv("OPSPILOT_CSRF_RELAX_DEV", "1")
    reset_db_engine()


# H1: sync_drain queued|running → abandoned with api_restart on startup


def test_lifespan_abandons_sync_drain(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
    test_database_url: str,
) -> None:
    """Startup abandons sync_drain jobs with queued|running status."""
    # Seed a running sync_drain job with a lease.
    job = insert_ops_job(
        db_session,
        job_kind="sync_drain",
        day_utc=date(2026, 10, 1),
        status="running",
    )
    upsert_lease(
        db_session,
        job_id=job.id,
        heartbeat_at=datetime.now(UTC),
        generation=5,
    )
    db_session.commit()
    job_id = job.id

    # Using context manager triggers lifespan startup.
    _setup_env(monkeypatch, test_database_url)
    with TestClient(create_app(), raise_server_exceptions=False) as client:
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200

    # Check the job is now abandoned.
    db_session.expire_all()
    job = db_session.get(OpsJobRow, job_id)
    assert job is not None
    assert job.status == "abandoned"
    assert job.error_code == "api_restart"

    # Lease should be cleared.
    lease = db_session.get(OpsJobLeaseRow, LEASE_SLOT)
    assert lease is None or lease.job_id is None


# H2: morning jobs NOT abandoned by lifespan


def test_lifespan_leaves_morning_jobs(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
    test_database_url: str,
) -> None:
    """Startup does NOT abandon morning jobs."""
    morning_job = insert_ops_job(
        db_session,
        job_kind="morning",
        day_utc=date(2026, 10, 1),
        status="running",
    )
    db_session.commit()
    morning_id = morning_job.id

    _setup_env(monkeypatch, test_database_url)
    with TestClient(create_app(), raise_server_exceptions=False) as client:
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200

    db_session.expire_all()
    job = db_session.get(OpsJobRow, morning_id)
    assert job is not None
    assert job.status == "running"  # NOT abandoned
