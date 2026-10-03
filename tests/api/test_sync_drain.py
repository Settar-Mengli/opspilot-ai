"""POST /sync drain-based (B6 C5): not_needed / started / busy."""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from typing import Any

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from opspilot.api.app import create_app
from opspilot.api.deps import reset_db_engine
from opspilot.persistence.models import OpsJobRow
from opspilot.persistence.repositories import oauth_credentials, work_items
from opspilot.persistence.repositories.ops_jobs import upsert_lease
from opspilot.services.operator_session import issue_session


@pytest.fixture
def sync_client(monkeypatch: pytest.MonkeyPatch, test_database_url: str) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("OPSPILOT_SESSION_SECRET", "test-session-secret-not-real")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "csec")
    monkeypatch.setenv("OPSPILOT_DEMO_MODE", "0")
    monkeypatch.setenv("OPSPILOT_FORCE_RULES", "1")
    monkeypatch.setenv("OPSPILOT_CSRF_RELAX_DEV", "1")
    reset_db_engine()
    return TestClient(create_app(), raise_server_exceptions=False)


def _seed_oauth(db_session: Session) -> None:
    oauth_credentials.upsert_encrypted_refresh(
        db_session,
        provider="google",
        account_email="demo@example.com",
        scopes="https://www.googleapis.com/auth/gmail.readonly",
        refresh_token_plaintext="rt",
    )
    db_session.commit()


def _noop_sync(session: Any, **kwargs: Any) -> dict[str, Any]:
    """Fake google sync that returns zeros (no real network)."""
    return {
        "account_email": "demo@example.com",
        "gmail_upserted": 0,
        "gmail_removed": 0,
        "calendar_upserted": 0,
        "gmail_total": 5,
        "meetings_total": 2,
        "gmail_truncated": False,
        "calendar_truncated": False,
    }


def _auth_headers(sync_client: TestClient) -> None:
    token = issue_session(email="demo@example.com")
    sync_client.cookies.set("opspilot_operator", token)


# ── not_needed (200) ──


def test_sync_not_needed_zero_pending(
    sync_client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No untriaged items → drain=not_needed, status 200."""
    _seed_oauth(db_session)
    monkeypatch.setattr("opspilot.api.v1.oauth_routes.google_sync.run_sync", _noop_sync)
    _auth_headers(sync_client)

    resp = sync_client.post("/api/v1/sync")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["drain"] == "not_needed"
    assert body["job_id"] is None
    assert body["pending"] == 0
    assert body["triaged"] == 0
    assert body["gmail_total"] == 5


# ── started (202) ──


def test_sync_started_with_pending(
    sync_client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Untriaged items + idle lease → drain=started, status 202, job_id present."""
    _seed_oauth(db_session)

    # Seed two untriaged gmail items.
    t0 = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    work_items.upsert_by_provider_id(
        db_session,
        provider_id="msg_a",
        source_type="gmail",
        subject_or_title="A",
        body_or_description="body",
        sender_or_requester="a@example.com",
        received_at=t0,
    )
    work_items.upsert_by_provider_id(
        db_session,
        provider_id="msg_b",
        source_type="gmail",
        subject_or_title="B",
        body_or_description="body",
        sender_or_requester="b@example.com",
        received_at=t0,
    )
    db_session.commit()

    monkeypatch.setattr("opspilot.api.v1.oauth_routes.google_sync.run_sync", _noop_sync)

    # Block drain from actually running (we only test the HTTP response shape).
    spawn_called = threading.Event()
    _orig_spawn = None

    def _fake_spawn(job_id: str, generation: int, ceiling: int) -> None:
        spawn_called.set()

    monkeypatch.setattr("opspilot.api.v1.oauth_routes._spawn_sync_drain", _fake_spawn)
    _auth_headers(sync_client)

    resp = sync_client.post("/api/v1/sync")
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert body["drain"] == "started"
    assert body["job_id"] is not None
    assert body["pending"] == 2

    # Verify the job row was created.
    db_session.expire_all()
    job = db_session.get(OpsJobRow, body["job_id"])
    assert job is not None
    assert job.job_kind == "sync_drain"
    assert job.status in ("queued", "running")


# ── busy (200) ──


def test_sync_busy_when_lease_held(
    sync_client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Lease held by another job → drain=busy, status 200, no new job inserted."""
    _seed_oauth(db_session)

    t0 = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    work_items.upsert_by_provider_id(
        db_session,
        provider_id="msg_c",
        source_type="gmail",
        subject_or_title="C",
        body_or_description="body",
        sender_or_requester="c@example.com",
        received_at=t0,
    )
    db_session.commit()

    # Simulate an existing lease held by another job.
    from datetime import date

    from opspilot.persistence.repositories.ops_jobs import insert_ops_job

    existing_job = insert_ops_job(
        db_session,
        job_kind="sync_drain",
        day_utc=date(2026, 10, 1),
        status="running",
    )
    upsert_lease(
        db_session,
        job_id=existing_job.id,
        heartbeat_at=datetime.now(UTC),
        generation=99,
    )
    db_session.commit()

    monkeypatch.setattr("opspilot.api.v1.oauth_routes.google_sync.run_sync", _noop_sync)
    _auth_headers(sync_client)

    resp = sync_client.post("/api/v1/sync")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["drain"] == "busy"
    assert body["job_id"] is None
    assert body["pending"] == 1


# ── CSRF enforcement ──


def test_sync_csrf_enforced(
    sync_client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without CSRF relax, missing Origin → 403."""
    _seed_oauth(db_session)
    monkeypatch.setenv("OPSPILOT_CSRF_RELAX_DEV", "0")
    monkeypatch.setattr("opspilot.api.v1.oauth_routes.google_sync.run_sync", _noop_sync)
    _auth_headers(sync_client)

    resp = sync_client.post("/api/v1/sync")
    assert resp.status_code == 403, resp.text
    body = resp.json()
    assert body["error"]["code"] == "csrf_origin_rejected"


# ── GET /jobs/{job_id} ──


def test_get_job_status(
    sync_client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GET /api/v1/jobs/{job_id} returns job fields."""
    from datetime import date

    from opspilot.persistence.repositories.ops_jobs import insert_ops_job

    job = insert_ops_job(
        db_session,
        job_kind="sync_drain",
        day_utc=date(2026, 10, 1),
        status="succeeded",
    )
    db_session.commit()
    _auth_headers(sync_client)

    resp = sync_client.get(f"/api/v1/jobs/{job.id}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == job.id
    assert body["job_kind"] == "sync_drain"
    assert body["status"] == "succeeded"


def test_get_job_status_not_found(
    sync_client: TestClient,
    db_session: Session,
) -> None:
    """GET /api/v1/jobs/nonexistent → 404."""
    _auth_headers(sync_client)
    resp = sync_client.get("/api/v1/jobs/oj_nonexistent")
    assert resp.status_code == 404


def test_get_job_status_no_auth(
    sync_client: TestClient,
) -> None:
    """GET /api/v1/jobs/{id} without cookie → 401."""
    resp = sync_client.get("/api/v1/jobs/oj_any")
    assert resp.status_code == 401
