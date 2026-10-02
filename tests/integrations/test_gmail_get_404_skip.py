"""Skip Gmail messages.get 404 during sync (history/list race)."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from cryptography.fernet import Fernet
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from opspilot.persistence.models import WorkItemRow
from opspilot.persistence.repositories import oauth_credentials, sync_cursors
from opspilot.services import google_sync


class _Get404Transport:
    """History returns two ids; first get 404s, second succeeds — sync must not abort."""

    def __init__(self) -> None:
        self.get_calls = 0

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        del method, headers, params, data, json
        if "oauth2.googleapis.com/token" in url:
            return httpx.Response(200, json={"access_token": "ya29.fake"})
        if url.endswith("/users/me/profile"):
            return httpx.Response(200, json={"historyId": "5000"})
        if "/users/me/history" in url:
            return httpx.Response(
                200,
                json={
                    "history": [
                        {"messagesAdded": [{"message": {"id": "gone_id"}}]},
                        {"messagesAdded": [{"message": {"id": "alive_id"}}]},
                    ]
                },
            )
        if "/users/me/messages/" in url:
            self.get_calls += 1
            mid = url.rsplit("/", 1)[-1]
            if mid == "gone_id":
                return httpx.Response(404, json={"error": {"code": 404, "message": "Not Found"}})
            return httpx.Response(
                200,
                json={
                    "id": mid,
                    "threadId": "thr",
                    "labelIds": ["INBOX"],
                    "payload": {
                        "headers": [
                            {"name": "Subject", "value": "S"},
                            {"name": "From", "value": "x@example.com"},
                            {"name": "Date", "value": "Tue, 30 Sep 2026 12:00:00 +0000"},
                        ],
                        "mimeType": "text/plain",
                        "body": {"data": "Ym9keQ"},
                    },
                },
            )
        return httpx.Response(500, json={"error": "unexpected"})


@pytest.fixture
def sync_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "csec")


def test_sync_skips_gmail_get_404_continues(db_session: Session, sync_env: None) -> None:
    oauth_credentials.upsert_encrypted_refresh(
        db_session,
        provider="google",
        account_email="demo@example.com",
        scopes=(
            "https://www.googleapis.com/auth/gmail.readonly "
            "https://www.googleapis.com/auth/gmail.send "
            "https://www.googleapis.com/auth/calendar.readonly"
        ),
        refresh_token_plaintext="rt",
    )
    sync_cursors.upsert_cursor(
        db_session,
        provider="google",
        account_email="demo@example.com",
        cursor_kind=sync_cursors.CURSOR_GMAIL_HISTORY,
        cursor_value="1000",
    )
    db_session.commit()

    tx = _Get404Transport()
    result = google_sync.run_sync(db_session, transport=tx, providers=["gmail"])
    db_session.commit()
    assert tx.get_calls == 2
    assert result["gmail_upserted"] == 1
    assert (
        db_session.scalar(select(func.count()).select_from(WorkItemRow).where(WorkItemRow.provider_id == "alive_id"))
        == 1
    )
    assert (
        db_session.scalar(select(func.count()).select_from(WorkItemRow).where(WorkItemRow.provider_id == "gone_id"))
        == 0
    )
