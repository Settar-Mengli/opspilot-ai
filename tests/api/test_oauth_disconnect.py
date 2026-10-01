"""DELETE /oauth/google disconnect clears credential and cookie; keeps work items."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from opspilot.api.app import create_app
from opspilot.api.deps import reset_db_engine
from opspilot.persistence.models import WorkItemRow
from opspilot.persistence.repositories import oauth_credentials, sync_cursors, work_items
from opspilot.services.operator_session import issue_session


@pytest.fixture
def disconnect_client(monkeypatch: pytest.MonkeyPatch, test_database_url: str) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("OPSPILOT_SESSION_SECRET", "test-session-secret-not-real")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "csec")
    monkeypatch.setenv("OPSPILOT_DEMO_MODE", "0")
    reset_db_engine()
    return TestClient(create_app())


def test_disconnect_clears_credential_keeps_gmail(
    disconnect_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    oauth_credentials.upsert_encrypted_refresh(
        db_session,
        provider="google",
        account_email="demo@example.com",
        scopes=("https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/calendar.readonly"),
        refresh_token_plaintext="rt",
    )
    sync_cursors.upsert_cursor(
        db_session,
        provider="google",
        account_email="demo@example.com",
        cursor_kind=sync_cursors.CURSOR_GMAIL_HISTORY,
        cursor_value="hist-1",
    )
    work_items.upsert_by_provider_id(
        db_session,
        provider_id="keep-me",
        source_type="gmail",
        subject_or_title="Keep",
        body_or_description="body",
        sender_or_requester="a@example.com",
        received_at=datetime(2026, 10, 1, tzinfo=UTC),
    )
    db_session.commit()
    assert oauth_credentials.is_connected(db_session) is True

    revoked: list[str] = []

    def _fake_revoke(token: str, **kwargs: object) -> None:
        revoked.append(token)

    monkeypatch.setattr("opspilot.api.v1.oauth_routes.revoke_refresh_token", _fake_revoke)
    token = issue_session(email="demo@example.com")
    disconnect_client.cookies.set("opspilot_operator", token)

    resp = disconnect_client.delete("/api/v1/oauth/google")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "disconnected"
    assert revoked == ["rt"]
    assert oauth_credentials.is_connected(db_session) is False
    assert db_session.scalar(select(func.count()).select_from(WorkItemRow)) == 1
    assert (
        sync_cursors.get_cursor(
            db_session,
            provider="google",
            account_email="demo@example.com",
            cursor_kind=sync_cursors.CURSOR_GMAIL_HISTORY,
        )
        is None
    )
