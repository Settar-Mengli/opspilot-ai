"""POST /sync drain-based response and error handling (B6 C5, formerly G6)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.integrations.test_google_sync import FakeTransport

from opspilot.api.app import create_app
from opspilot.api.deps import get_db_session, reset_db_engine
from opspilot.integrations.google_http import GoogleHttpError
from opspilot.persistence.repositories import oauth_credentials, work_items
from opspilot.services import google_sync
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
    reset_db_engine()
    return TestClient(create_app(), raise_server_exceptions=False)


def _seed_oauth(db_session: Session) -> None:
    oauth_credentials.upsert_encrypted_refresh(
        db_session,
        provider="google",
        account_email="demo@example.com",
        scopes=(
            "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/calendar.readonly"
        ),
        refresh_token_plaintext="rt",
    )
    db_session.commit()


def _patch_sync(monkeypatch: pytest.MonkeyPatch) -> None:
    real_sync = google_sync.run_sync

    def _run(session: Any, **kwargs: Any) -> dict[str, Any]:
        kwargs.pop("transport", None)
        return real_sync(session, transport=FakeTransport(), **kwargs)

    monkeypatch.setattr("opspilot.api.v1.oauth_routes.google_sync.run_sync", _run)


def test_post_sync_drain_started_with_items(
    sync_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FakeTransport seeds 2 gmail items → drain=started, 202, sync counts present."""
    _seed_oauth(db_session)
    _patch_sync(monkeypatch)
    monkeypatch.setattr("opspilot.api.v1.oauth_routes._spawn_sync_drain", lambda *a: None)
    token = issue_session(email="demo@example.com")
    sync_client.cookies.set("opspilot_operator", token)

    resp = sync_client.post("/api/v1/sync")
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert body["drain"] == "started"
    assert body["gmail_upserted"] == 2
    assert body["calendar_upserted"] == 1
    assert body["pending"] == 2
    assert body["job_id"] is not None


def test_post_sync_google_http_error_returns_envelope(
    sync_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_oauth(db_session)

    def _boom(session: Any, **kwargs: Any) -> dict[str, Any]:
        raise GoogleHttpError("calendar_list_failed", status_code=400)

    monkeypatch.setattr("opspilot.api.v1.oauth_routes.google_sync.run_sync", _boom)
    token = issue_session(email="demo@example.com")
    sync_client.cookies.set("opspilot_operator", token)

    resp = sync_client.post("/api/v1/sync")
    assert resp.status_code == 502
    body = resp.json()
    assert body["error"]["code"] == "calendar_list_failed"
    assert body["error"]["details"]["upstream_status"] == 400
    assert "request_id" in body["error"]
    assert "Traceback" not in resp.text
    assert "ya29" not in resp.text


def test_list_gmail_untriaged_skips_decided(db_session: Session) -> None:
    from opspilot.persistence.models import TriageDecisionRow

    t0 = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)
    wid_a = work_items.upsert_by_provider_id(
        db_session,
        provider_id="pa",
        source_type="gmail",
        subject_or_title="A",
        body_or_description="body",
        sender_or_requester="a@example.com",
        received_at=t0,
    )
    work_items.upsert_by_provider_id(
        db_session,
        provider_id="pb",
        source_type="gmail",
        subject_or_title="B",
        body_or_description="body",
        sender_or_requester="b@example.com",
        received_at=t0.replace(hour=13),
    )
    db_session.add(
        TriageDecisionRow(
            work_item_id=wid_a,
            run_id=None,
            urgency="low",
            urgency_reason="r",
            category="other",
            category_reason="r",
            sentiment="neutral",
            sentiment_reason="r",
        )
    )
    db_session.flush()
    raw = work_items.list_gmail_untriaged_raw(db_session, limit=10)
    assert len(raw) == 1
    assert raw[0]["provider_id"] == "pb"
    assert work_items.count_gmail_untriaged(db_session) == 1


def test_get_db_session_rollback_failed_reraises_original(
    monkeypatch: pytest.MonkeyPatch, test_database_url: str
) -> None:
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    reset_db_engine()

    from opspilot.api import deps as deps_mod

    factory = deps_mod._get_factory()
    original_factory = factory

    class _BoomSession:
        def commit(self) -> None:
            return None

        def rollback(self) -> None:
            raise RuntimeError("received 2 results from command 'ROLLBACK'")

        def close(self) -> None:
            return None

        def __enter__(self) -> _BoomSession:
            return self

        def __exit__(self, *a: Any) -> None:
            return None

    class _BoomFactory:
        def __call__(self) -> _BoomSession:
            return _BoomSession()

    monkeypatch.setattr(deps_mod, "_get_factory", lambda: _BoomFactory())

    gen = get_db_session()
    next(gen)
    with pytest.raises(ValueError, match="original"):
        gen.throw(ValueError("original"))

    monkeypatch.setattr(deps_mod, "_get_factory", lambda: original_factory)
    reset_db_engine()


def test_connected_post_runs_respects_cap(
    sync_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """POST /runs with connected Gmail still uses triage_connected_gmail path."""
    monkeypatch.setenv("OPSPILOT_SYNC_TRIAGE_CAP", "1")
    _seed_oauth(db_session)
    _patch_sync(monkeypatch)
    monkeypatch.setattr("opspilot.api.v1.oauth_routes._spawn_sync_drain", lambda *a: None)
    token = issue_session(email="demo@example.com")
    sync_client.cookies.set("opspilot_operator", token)

    # Seed gmail rows via Sync (drain=started but no actual drain).
    resp_sync = sync_client.post("/api/v1/sync")
    assert resp_sync.status_code == 202, resp_sync.text
    assert resp_sync.json()["gmail_upserted"] == 2

    monkeypatch.setenv("OPSPILOT_SYNC_TRIAGE_CAP", "1")
    resp = sync_client.post("/api/v1/runs", json={"date": "2026-10-01"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["triaged"] == 1
    assert body["pending"] == 1
