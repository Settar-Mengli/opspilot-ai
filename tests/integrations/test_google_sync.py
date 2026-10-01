"""Hermetic Gmail parse + sync idempotency with fake transport."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from cryptography.fernet import Fernet
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from opspilot.integrations.gmail_client import parse_message
from opspilot.persistence.models import MeetingRow, WorkItemRow
from opspilot.persistence.repositories import oauth_credentials
from opspilot.services import google_sync


def test_parse_message_skips_attachments() -> None:
    raw = {
        "id": "m1",
        "threadId": "t1",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Hi"},
                {"name": "From", "value": "a@example.com"},
                {"name": "Date", "value": "Tue, 30 Sep 2026 12:00:00 +0000"},
            ],
            "mimeType": "multipart/mixed",
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {"data": "SGVsbG8gd29ybGQ"},  # Hello world
                },
                {
                    "filename": "file.pdf",
                    "mimeType": "application/pdf",
                    "body": {"data": "AAAA"},
                },
            ],
        },
    }
    msg = parse_message(raw)
    assert msg.provider_id == "m1"
    assert "Hello world" in msg.body
    assert "AAAA" not in msg.body


class FakeTransport:
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
    ) -> httpx.Response:
        self.calls.append((method, url))
        if "oauth2.googleapis.com/token" in url:
            return httpx.Response(200, json={"access_token": "ya29.fake"})
        if url.endswith("/users/me/profile"):
            return httpx.Response(200, json={"historyId": "999"})
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
                        "body": {"data": "Ym9keQ"},  # body
                    },
                },
            )
        if url.endswith("/users/me/messages"):
            return httpx.Response(200, json={"messages": [{"id": "m1"}, {"id": "m2"}]})
        if "/users/me/history" in url:
            return httpx.Response(404, json={"error": "expired"})
        if "/calendars/primary/events" in url:
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": "e1",
                            "summary": "Demo sync",
                            "start": {"dateTime": "2026-09-30T15:00:00Z"},
                            "end": {"dateTime": "2026-09-30T16:00:00Z"},
                        }
                    ],
                    "nextSyncToken": "cal-token-1",
                },
            )
        return httpx.Response(500, text=json.dumps({"error": "unexpected"}))


@pytest.fixture
def sync_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "csec")


def test_sync_idempotent(db_session: Session, sync_env: None) -> None:
    oauth_credentials.upsert_encrypted_refresh(
        db_session,
        provider="google",
        account_email="demo@example.com",
        scopes=("https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/calendar.readonly"),
        refresh_token_plaintext="rt",
    )
    tx = FakeTransport()
    r1 = google_sync.run_sync(db_session, transport=tx)
    r2 = google_sync.run_sync(db_session, transport=tx)
    assert r1["gmail_upserted"] == 2
    assert r2["gmail_upserted"] == 2
    assert db_session.scalar(select(func.count()).select_from(WorkItemRow)) == 2
    assert db_session.scalar(select(func.count()).select_from(MeetingRow)) == 1
    assert r1["calendar_upserted"] == 1
