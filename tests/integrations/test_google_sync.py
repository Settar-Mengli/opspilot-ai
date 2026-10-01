"""Hermetic Gmail parse + sync idempotency with fake transport."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
from cryptography.fernet import Fernet
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from opspilot.integrations.calendar_client import CalendarClient
from opspilot.integrations.gmail_client import parse_message
from opspilot.persistence.models import MeetingRow, WorkItemRow
from opspilot.persistence.repositories import meetings, oauth_credentials, sync_cursors
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


_FORBIDDEN_WITH_SYNC = frozenset({"showDeleted", "timeMin", "timeMax", "orderBy", "singleEvents"})


class FakeTransport:
    """Mirrors Google Calendar syncToken rules: 400 if syncToken + window params."""

    def __init__(
        self,
        *,
        calendar_mode: str = "ok",
        calendar_items: list[dict[str, Any]] | None = None,
    ) -> None:
        self.calls: list[tuple[str, str]] = []
        self.calendar_params: list[dict[str, Any]] = []
        self.calendar_mode = calendar_mode
        self.calendar_items = calendar_items

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
            p = dict(params or {})
            self.calendar_params.append(p)
            if "syncToken" in p and _FORBIDDEN_WITH_SYNC.intersection(p):
                return httpx.Response(400, json={"error": {"message": "syncToken with forbidden params"}})
            if self.calendar_mode == "410" and "syncToken" in p:
                return httpx.Response(410, json={"error": {"message": "gone"}})
            items = self.calendar_items
            if items is None:
                items = [
                    {
                        "id": "e1",
                        "summary": "Demo sync",
                        "start": {"dateTime": "2026-09-30T15:00:00Z"},
                        "end": {"dateTime": "2026-09-30T16:00:00Z"},
                    }
                ]
            return httpx.Response(
                200,
                json={
                    "items": items,
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
        scopes=(
            "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/calendar.readonly"
        ),
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
    # Second calendar call must use syncToken without window/order params
    assert len(tx.calendar_params) >= 2
    incr = tx.calendar_params[1]
    assert incr.get("syncToken") == "cal-token-1"
    assert "showDeleted" not in incr
    assert "timeMin" not in incr
    assert "timeMax" not in incr
    assert "orderBy" not in incr
    assert "singleEvents" not in incr


def test_list_events_sync_token_sends_only_token() -> None:
    tx = FakeTransport()
    client = CalendarClient(access_token="t", transport=tx)
    now = datetime.now(UTC)
    client.list_events(time_min=now, time_max=now + timedelta(days=7), sync_token="tok")
    assert tx.calendar_params[-1] == {"syncToken": "tok"}


def test_fake_transport_400_when_sync_token_combined_with_window() -> None:
    tx = FakeTransport()
    resp = tx.request(
        "GET",
        "https://www.googleapis.com/calendar/v3/calendars/primary/events",
        params={
            "syncToken": "x",
            "showDeleted": "false",
            "timeMin": "2026-01-01T00:00:00Z",
            "timeMax": "2026-01-08T00:00:00Z",
            "orderBy": "startTime",
        },
    )
    assert resp.status_code == 400


def test_calendar_410_triggers_full_resync(db_session: Session, sync_env: None) -> None:
    oauth_credentials.upsert_encrypted_refresh(
        db_session,
        provider="google",
        account_email="demo@example.com",
        scopes=(
            "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/calendar.readonly"
        ),
        refresh_token_plaintext="rt",
    )
    sync_cursors.upsert_cursor(
        db_session,
        provider="google",
        account_email="demo@example.com",
        cursor_kind=sync_cursors.CURSOR_CALENDAR_SYNC,
        cursor_value="stale-token",
    )
    tx = FakeTransport(calendar_mode="410")
    result = google_sync.run_sync(db_session, transport=tx)
    assert result["calendar_upserted"] == 1
    # First calendar call: syncToken -> 410; second: full window
    assert any("syncToken" in p for p in tx.calendar_params)
    full = [p for p in tx.calendar_params if "syncToken" not in p]
    assert full
    assert "timeMin" in full[0]
    assert "timeMax" in full[0]


def test_cancelled_incremental_deletes_meeting(db_session: Session, sync_env: None) -> None:
    oauth_credentials.upsert_encrypted_refresh(
        db_session,
        provider="google",
        account_email="demo@example.com",
        scopes=(
            "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/calendar.readonly"
        ),
        refresh_token_plaintext="rt",
    )
    start = datetime(2026, 9, 30, 15, 0, tzinfo=UTC)
    end = datetime(2026, 9, 30, 16, 0, tzinfo=UTC)
    meetings.upsert_by_provider_id(
        db_session,
        provider_id="e1",
        title="Demo sync",
        start_at=start,
        end_at=end,
    )
    sync_cursors.upsert_cursor(
        db_session,
        provider="google",
        account_email="demo@example.com",
        cursor_kind=sync_cursors.CURSOR_CALENDAR_SYNC,
        cursor_value="cal-token-0",
    )
    tx = FakeTransport(
        calendar_items=[{"id": "e1", "status": "cancelled"}],
    )
    google_sync.run_sync(db_session, transport=tx)
    assert db_session.scalar(select(func.count()).select_from(MeetingRow)) == 0
    incr = tx.calendar_params[0]
    assert incr.get("syncToken") == "cal-token-0"
    assert "showDeleted" not in incr
    assert "timeMin" not in incr
