"""Sync drain Anthropic operator auth (F2) — hermetic via POST /sync."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from opspilot.api.app import create_app
from opspilot.api.deps import reset_db_engine
from opspilot.llm.operator_auth import OperatorAnthropicAuth
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
    return {
        "account_email": "demo@example.com",
        "gmail_upserted": 0,
        "gmail_removed": 0,
        "calendar_upserted": 0,
        "gmail_total": 1,
        "meetings_total": 0,
        "gmail_truncated": False,
        "calendar_truncated": False,
    }


def _seed_one_untriaged(db_session: Session) -> None:
    t0 = datetime.now(UTC)
    work_items.upsert_by_provider_id(
        db_session,
        provider_id="msg_auth_1",
        source_type="gmail",
        subject_or_title="A",
        body_or_description="body",
        sender_or_requester="a@example.test",
        received_at=t0,
    )
    db_session.commit()


def test_authorized_sync_passes_auth_to_drain(
    sync_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_oauth(db_session)
    _seed_one_untriaged(db_session)
    monkeypatch.setattr("opspilot.api.v1.oauth_routes.google_sync.run_sync", _noop_sync)
    captured: list[object | None] = []

    def _fake_spawn(job_id: str, generation: int, ceiling: int, operator_auth: object | None = None) -> None:
        captured.append(operator_auth)

    monkeypatch.setattr("opspilot.api.v1.oauth_routes._spawn_sync_drain", _fake_spawn)
    token = issue_session(email="demo@example.com")
    sync_client.cookies.set("opspilot_operator", token)
    resp = sync_client.post("/api/v1/sync")
    assert resp.status_code == 202, resp.text
    assert len(captured) == 1
    assert isinstance(captured[0], OperatorAnthropicAuth)
    assert captured[0].role == "demo_operator"


def test_busy_lease_does_not_spawn_auth_unchanged(
    sync_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_oauth(db_session)
    _seed_one_untriaged(db_session)
    monkeypatch.setattr("opspilot.api.v1.oauth_routes.google_sync.run_sync", _noop_sync)
    # Hold lease with a running job
    other = OpsJobRow(
        id="running-job",
        job_kind="sync_drain",
        day_utc=datetime.now(UTC).date(),
        status="running",
        force_override=False,
        request_ceiling=10,
        metadata_json={},
    )
    db_session.add(other)
    db_session.flush()
    upsert_lease(db_session, job_id="running-job", generation=1)
    db_session.commit()

    spawns: list[Any] = []

    def _fake_spawn(*args: Any, **kwargs: Any) -> None:
        spawns.append((args, kwargs))

    monkeypatch.setattr("opspilot.api.v1.oauth_routes._spawn_sync_drain", _fake_spawn)
    token = issue_session(email="demo@example.com")
    sync_client.cookies.set("opspilot_operator", token)
    resp = sync_client.post("/api/v1/sync")
    assert resp.status_code == 200, resp.text
    assert resp.json()["drain"] == "busy"
    assert spawns == []


def test_sequential_authorized_then_no_auth_sees_none(
    sync_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two sequential Sync starts on one thread: auth then no-cookie path → second sees None."""
    _seed_oauth(db_session)
    monkeypatch.setattr("opspilot.api.v1.oauth_routes.google_sync.run_sync", _noop_sync)
    captured: list[object | None] = []

    def _fake_spawn(job_id: str, generation: int, ceiling: int, operator_auth: object | None = None) -> None:
        captured.append(operator_auth)

    monkeypatch.setattr("opspilot.api.v1.oauth_routes._spawn_sync_drain", _fake_spawn)

    # First: authorized + pending → started
    _seed_one_untriaged(db_session)
    token = issue_session(email="demo@example.com")
    sync_client.cookies.set("opspilot_operator", token)
    r1 = sync_client.post("/api/v1/sync")
    assert r1.status_code == 202, r1.text
    assert isinstance(captured[0], OperatorAnthropicAuth)

    # Clear cookie; seed another item; claim lease free again by releasing via not holding
    sync_client.cookies.clear()
    # Force idle lease: update lease to free if prior spawn didn't run
    from sqlalchemy import text

    db_session.execute(text("UPDATE ops_job_lease SET job_id = NULL, heartbeat_at = NULL WHERE slot = 1"))
    db_session.commit()
    work_items.upsert_by_provider_id(
        db_session,
        provider_id="msg_auth_2",
        source_type="gmail",
        subject_or_title="B",
        body_or_description="body",
        sender_or_requester="b@example.test",
        received_at=datetime.now(UTC),
    )
    db_session.commit()
    # Second request without cookie still needs operator cookie for Sync itself —
    # Sync requires operator session. Use a cookie that verify_session rejects
    # so from_session → None while Sync auth gate still passes... Sync checks cookie.
    # Use valid cookie then monkeypatch from_session for the second call only.
    sync_client.cookies.set("opspilot_operator", token)
    captured.clear()
    monkeypatch.setattr(
        "opspilot.llm.operator_auth.OperatorAnthropicAuth.from_session",
        lambda session: None,
    )
    r2 = sync_client.post("/api/v1/sync")
    assert r2.status_code == 202, r2.text
    assert len(captured) == 1
    assert captured[0] is None


def test_pin_no_operator_auth_contextvar_in_src() -> None:
    root = Path("src")
    hits: list[str] = []
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "ContextVar" in text and ("operator_auth" in text or "sync_drain_operator" in text):
            hits.append(path.as_posix())
        if "_sync_drain_operator_auth" in text:
            hits.append(path.as_posix())
    assert hits == [], hits
