"""POST /sync runs triage after a successful Google sync."""

from __future__ import annotations

from typing import Any

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.integrations.test_google_sync import FakeTransport

from opspilot.api.app import create_app
from opspilot.api.deps import reset_db_engine
from opspilot.persistence.models import TriageDecisionRow
from opspilot.persistence.repositories import oauth_credentials
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
    return TestClient(create_app())


def test_post_sync_returns_triaged_count(
    sync_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    oauth_credentials.upsert_encrypted_refresh(
        db_session,
        provider="google",
        account_email="demo@example.com",
        scopes=("https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/calendar.readonly"),
        refresh_token_plaintext="rt",
    )
    db_session.commit()

    real_sync = google_sync.run_sync

    def _run(session: Any, **kwargs: Any) -> dict[str, Any]:
        kwargs.pop("transport", None)
        return real_sync(session, transport=FakeTransport(), **kwargs)

    monkeypatch.setattr("opspilot.api.v1.oauth_routes.google_sync.run_sync", _run)
    token = issue_session(email="demo@example.com")
    sync_client.cookies.set("opspilot_operator", token)

    resp = sync_client.post("/api/v1/sync")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["gmail_upserted"] == 2
    assert body["calendar_upserted"] == 1
    assert body["triaged"] == 2
    assert body["run_id"]
    decisions = db_session.scalars(select(TriageDecisionRow).where(TriageDecisionRow.run_id == body["run_id"])).all()
    assert len(decisions) == 2
