"""Gmail deleted-message removal on incremental sync."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from cryptography.fernet import Fernet
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from opspilot.persistence.models import WorkItemRow
from opspilot.persistence.repositories import oauth_credentials, sync_cursors, work_items
from opspilot.services import google_sync


class _DeleteAwareTransport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

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
        del headers, data, json
        self.calls.append((method, url))
        if "oauth2.googleapis.com/token" in url:
            return httpx.Response(200, json={"access_token": "ya29.fake"})
        if url.endswith("/users/me/profile"):
            return httpx.Response(200, json={"historyId": "2000"})
        if "/users/me/history" in url:
            return httpx.Response(
                200,
                json={
                    "history": [
                        {"messagesDeleted": [{"message": {"id": "gone_msg"}}]},
                        {"messagesAdded": [{"message": {"id": "new_msg"}}]},
                    ]
                },
            )
        if "/users/me/messages/" in url and not url.endswith("/messages"):
            mid = url.rsplit("/", 1)[-1]
            return httpx.Response(
                200,
                json={
                    "id": mid,
                    "threadId": "thr",
                    "payload": {
                        "headers": [
                            {"name": "Subject", "value": f"Subj {mid}"},
                            {"name": "From", "value": "x@example.com"},
                            {"name": "Date", "value": "Tue, 30 Sep 2026 12:00:00 +0000"},
                        ],
                        "mimeType": "text/plain",
                        "body": {"data": "Ym9keQ"},
                    },
                },
            )
        if "/calendars/primary/events" in url:
            return httpx.Response(200, json={"items": [], "nextSyncToken": "t"})
        return httpx.Response(500, json={"error": "unexpected"})


@pytest.fixture
def sync_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "csec")


def test_sync_removes_deleted_gmail_messages(db_session: Session, sync_env: None) -> None:
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
    work_items.upsert_by_provider_id(
        db_session,
        provider_id="gone_msg",
        source_type="gmail",
        subject_or_title="Gone",
        body_or_description="Bye",
        sender_or_requester="x@example.com",
        received_at=datetime(2026, 9, 30, tzinfo=UTC),
        thread_id="thr",
    )
    sync_cursors.upsert_cursor(
        db_session,
        provider="google",
        account_email="demo@example.com",
        cursor_kind=sync_cursors.CURSOR_GMAIL_HISTORY,
        cursor_value="1000",
    )
    db_session.commit()
    assert (
        db_session.scalar(select(func.count()).select_from(WorkItemRow).where(WorkItemRow.provider_id == "gone_msg"))
        == 1
    )

    google_sync.run_sync(db_session, transport=_DeleteAwareTransport(), providers=["gmail"])
    db_session.commit()
    assert (
        db_session.scalar(select(func.count()).select_from(WorkItemRow).where(WorkItemRow.provider_id == "gone_msg"))
        == 0
    )
    assert (
        db_session.scalar(select(func.count()).select_from(WorkItemRow).where(WorkItemRow.provider_id == "new_msg"))
        == 1
    )
