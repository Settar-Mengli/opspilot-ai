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
                    "labelIds": ["INBOX"],
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
            q = str((params or {}).get("q") or "")
            if "trash" in q:
                return httpx.Response(200, json={"messages": []})
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


def test_calendar_truncated_incremental_clears_token_next_full_stores_token(
    db_session: Session, sync_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Google-faithful: same syncToken without pageToken always returns page 1."""
    monkeypatch.setenv("OPSPILOT_CALENDAR_LIST_MAX_PAGES", "1")
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
        cursor_kind=sync_cursors.CURSOR_CALENDAR_SYNC,
        cursor_value="cal-prior",
    )
    db_session.commit()

    class _GoogleFaithfulCal:
        def __init__(self) -> None:
            self.full_calls = 0

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
            del method, headers, data, json
            if "oauth2.googleapis.com/token" in url:
                return httpx.Response(200, json={"access_token": "ya29.fake"})
            if url.endswith("/users/me/profile"):
                return httpx.Response(200, json={"historyId": "1"})
            if "/users/me/history" in url:
                return httpx.Response(200, json={"history": []})
            if url.endswith("/users/me/messages"):
                return httpx.Response(200, json={"messages": []})
            if "/calendars/primary/events" in url:
                p = dict(params or {})
                # Incremental: same syncToken without pageToken → always page 1 (Google).
                if p.get("syncToken") == "cal-prior":
                    if p.get("pageToken"):
                        return httpx.Response(
                            200,
                            json={
                                "items": [
                                    {
                                        "id": "ev_page2",
                                        "summary": "Two",
                                        "start": {"dateTime": "2026-10-03T15:00:00Z"},
                                        "end": {"dateTime": "2026-10-03T16:00:00Z"},
                                    }
                                ],
                                "nextSyncToken": "cal-from-incr",
                            },
                        )
                    return httpx.Response(
                        200,
                        json={
                            "items": [
                                {
                                    "id": "ev_page1",
                                    "summary": "One",
                                    "start": {"dateTime": "2026-10-02T15:00:00Z"},
                                    "end": {"dateTime": "2026-10-02T16:00:00Z"},
                                }
                            ],
                            "nextPageToken": "calpage2",
                        },
                    )
                # Full window (no syncToken): complete in one page for second sync.
                if "timeMin" in p:
                    self.full_calls += 1
                    return httpx.Response(
                        200,
                        json={
                            "items": [
                                {
                                    "id": "ev_page1",
                                    "summary": "One",
                                    "start": {"dateTime": "2026-10-02T15:00:00Z"},
                                    "end": {"dateTime": "2026-10-02T16:00:00Z"},
                                },
                                {
                                    "id": "ev_full2",
                                    "summary": "FullTwo",
                                    "start": {"dateTime": "2026-10-03T15:00:00Z"},
                                    "end": {"dateTime": "2026-10-03T16:00:00Z"},
                                },
                            ],
                            "nextSyncToken": "cal-after-full",
                        },
                    )
                return httpx.Response(200, json={"items": [], "nextSyncToken": "cal-empty"})
            return httpx.Response(500, json={"error": "unexpected"})

    tx = _GoogleFaithfulCal()
    r1 = google_sync.run_sync(db_session, transport=tx, providers=["calendar"])
    db_session.commit()
    assert r1.get("calendar_truncated") is True
    assert (
        db_session.scalar(select(func.count()).select_from(MeetingRow).where(MeetingRow.provider_id == "ev_page1")) == 1
    )
    cur = sync_cursors.get_cursor(
        db_session,
        provider="google",
        account_email="demo@example.com",
        cursor_kind=sync_cursors.CURSOR_CALENDAR_SYNC,
    )
    assert cur is None

    monkeypatch.setenv("OPSPILOT_CALENDAR_LIST_MAX_PAGES", "20")
    r2 = google_sync.run_sync(db_session, transport=tx, providers=["calendar"])
    db_session.commit()
    assert r2.get("calendar_truncated") is False
    assert (
        db_session.scalar(select(func.count()).select_from(MeetingRow).where(MeetingRow.provider_id == "ev_full2")) == 1
    )
    cur2 = sync_cursors.get_cursor(
        db_session,
        provider="google",
        account_email="demo@example.com",
        cursor_kind=sync_cursors.CURSOR_CALENDAR_SYNC,
    )
    assert cur2 == "cal-after-full"
    assert tx.full_calls >= 1


def test_calendar_full_window_truncated_no_token_flag_true(
    db_session: Session, sync_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPSPILOT_CALENDAR_LIST_MAX_PAGES", "1")
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
    db_session.commit()

    class _TruncFull:
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
            del method, headers, data, json
            if "oauth2.googleapis.com/token" in url:
                return httpx.Response(200, json={"access_token": "ya29.fake"})
            if "/calendars/primary/events" in url:
                return httpx.Response(
                    200,
                    json={
                        "items": [
                            {
                                "id": "ev_only",
                                "summary": "Only",
                                "start": {"dateTime": "2026-10-02T12:00:00Z"},
                                "end": {"dateTime": "2026-10-02T13:00:00Z"},
                            }
                        ],
                        "nextPageToken": "more",
                    },
                )
            return httpx.Response(500, json={"error": "unexpected"})

    r = google_sync.run_sync(db_session, transport=_TruncFull(), providers=["calendar"])
    db_session.commit()
    assert r.get("calendar_truncated") is True
    assert (
        sync_cursors.get_cursor(
            db_session,
            provider="google",
            account_email="demo@example.com",
            cursor_kind=sync_cursors.CURSOR_CALENDAR_SYNC,
        )
        is None
    )


def test_calendar_cancelled_removed_on_full_resync(db_session: Session, sync_env: None) -> None:
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
    now = datetime.now(UTC)
    meetings.upsert_by_provider_id(
        db_session,
        provider_id="ev_cancel_me",
        title="Cancel",
        start_at=now + timedelta(hours=2),
        end_at=now + timedelta(hours=3),
    )
    db_session.commit()

    class _CancelTx:
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
            del method, headers, data, json
            if "oauth2.googleapis.com/token" in url:
                return httpx.Response(200, json={"access_token": "ya29.fake"})
            if "/calendars/primary/events" in url:
                p = dict(params or {})
                assert p.get("showDeleted") == "true"
                return httpx.Response(
                    200,
                    json={
                        "items": [{"id": "ev_cancel_me", "status": "cancelled"}],
                        "nextSyncToken": "cal-c",
                    },
                )
            return httpx.Response(500, json={"error": "unexpected"})

    google_sync.run_sync(db_session, transport=_CancelTx(), providers=["calendar"])
    db_session.commit()
    assert (
        db_session.scalar(select(func.count()).select_from(MeetingRow).where(MeetingRow.provider_id == "ev_cancel_me"))
        == 0
    )


def test_calendar_hard_deleted_absent_from_complete_full_window_removed(db_session: Session, sync_env: None) -> None:
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
    now = datetime.now(UTC)
    meetings.upsert_by_provider_id(
        db_session,
        provider_id="ev_gone",
        title="Gone",
        start_at=now + timedelta(hours=4),
        end_at=now + timedelta(hours=5),
    )
    meetings.upsert_by_provider_id(
        db_session,
        provider_id="ev_keep",
        title="Keep",
        start_at=now + timedelta(hours=6),
        end_at=now + timedelta(hours=7),
    )
    db_session.commit()

    class _AbsentTx:
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
            del method, headers, data, json
            if "oauth2.googleapis.com/token" in url:
                return httpx.Response(200, json={"access_token": "ya29.fake"})
            if "/calendars/primary/events" in url:
                return httpx.Response(
                    200,
                    json={
                        "items": [
                            {
                                "id": "ev_keep",
                                "summary": "Keep",
                                "start": {"dateTime": (now + timedelta(hours=6)).isoformat().replace("+00:00", "Z")},
                                "end": {"dateTime": (now + timedelta(hours=7)).isoformat().replace("+00:00", "Z")},
                            }
                        ],
                        "nextSyncToken": "cal-abs",
                    },
                )
            return httpx.Response(500, json={"error": "unexpected"})

    google_sync.run_sync(db_session, transport=_AbsentTx(), providers=["calendar"])
    db_session.commit()
    assert (
        db_session.scalar(select(func.count()).select_from(MeetingRow).where(MeetingRow.provider_id == "ev_gone")) == 0
    )
    assert (
        db_session.scalar(select(func.count()).select_from(MeetingRow).where(MeetingRow.provider_id == "ev_keep")) == 1
    )


def test_calendar_event_outside_window_untouched(db_session: Session, sync_env: None) -> None:
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
    now = datetime.now(UTC)
    meetings.upsert_by_provider_id(
        db_session,
        provider_id="ev_outside",
        title="Outside",
        start_at=now + timedelta(days=30),
        end_at=now + timedelta(days=30, hours=1),
    )
    db_session.commit()

    class _EmptyWindow:
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
            del method, headers, data, json, params
            if "oauth2.googleapis.com/token" in url:
                return httpx.Response(200, json={"access_token": "ya29.fake"})
            if "/calendars/primary/events" in url:
                return httpx.Response(200, json={"items": [], "nextSyncToken": "cal-empty"})
            return httpx.Response(500, json={"error": "unexpected"})

    google_sync.run_sync(db_session, transport=_EmptyWindow(), providers=["calendar"])
    db_session.commit()
    assert (
        db_session.scalar(select(func.count()).select_from(MeetingRow).where(MeetingRow.provider_id == "ev_outside"))
        == 1
    )


def test_calendar_truncated_full_window_skips_absence_reconcile(
    db_session: Session, sync_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPSPILOT_CALENDAR_LIST_MAX_PAGES", "1")
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
    now = datetime.now(UTC)
    meetings.upsert_by_provider_id(
        db_session,
        provider_id="ev_should_stay",
        title="Stay",
        start_at=now + timedelta(hours=2),
        end_at=now + timedelta(hours=3),
    )
    db_session.commit()

    class _TruncNoReconcile:
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
            del method, headers, data, json
            if "oauth2.googleapis.com/token" in url:
                return httpx.Response(200, json={"access_token": "ya29.fake"})
            if "/calendars/primary/events" in url:
                return httpx.Response(
                    200,
                    json={
                        "items": [
                            {
                                "id": "ev_other",
                                "summary": "Other",
                                "start": {"dateTime": (now + timedelta(hours=5)).isoformat().replace("+00:00", "Z")},
                                "end": {"dateTime": (now + timedelta(hours=6)).isoformat().replace("+00:00", "Z")},
                            }
                        ],
                        "nextPageToken": "more",
                    },
                )
            return httpx.Response(500, json={"error": "unexpected"})

    r = google_sync.run_sync(db_session, transport=_TruncNoReconcile(), providers=["calendar"])
    db_session.commit()
    assert r.get("calendar_truncated") is True
    assert (
        db_session.scalar(
            select(func.count()).select_from(MeetingRow).where(MeetingRow.provider_id == "ev_should_stay")
        )
        == 1
    )


def test_calendar_untruncated_incremental_unchanged(db_session: Session, sync_env: None) -> None:
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
        cursor_kind=sync_cursors.CURSOR_CALENDAR_SYNC,
        cursor_value="cal-prior",
    )
    db_session.commit()

    class _IncrOk:
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
            del method, headers, data, json
            if "oauth2.googleapis.com/token" in url:
                return httpx.Response(200, json={"access_token": "ya29.fake"})
            if "/calendars/primary/events" in url:
                p = dict(params or {})
                assert p.get("syncToken") == "cal-prior"
                assert "showDeleted" not in p
                return httpx.Response(
                    200,
                    json={
                        "items": [
                            {
                                "id": "ev_incr",
                                "summary": "Incr",
                                "start": {"dateTime": "2026-10-02T18:00:00Z"},
                                "end": {"dateTime": "2026-10-02T19:00:00Z"},
                            }
                        ],
                        "nextSyncToken": "cal-next-incr",
                    },
                )
            return httpx.Response(500, json={"error": "unexpected"})

    r = google_sync.run_sync(db_session, transport=_IncrOk(), providers=["calendar"])
    db_session.commit()
    assert r.get("calendar_truncated") is False
    assert (
        sync_cursors.get_cursor(
            db_session,
            provider="google",
            account_email="demo@example.com",
            cursor_kind=sync_cursors.CURSOR_CALENDAR_SYNC,
        )
        == "cal-next-incr"
    )


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
            "showDeleted": "true",
            "timeMin": "2026-01-01T00:00:00Z",
            "timeMax": "2026-01-08T00:00:00Z",
            "orderBy": "startTime",
        },
    )
    assert resp.status_code == 400


def test_full_window_sends_show_deleted_true() -> None:
    tx = FakeTransport()
    client = CalendarClient(access_token="t", transport=tx)
    now = datetime.now(UTC)
    client.list_events(time_min=now, time_max=now + timedelta(days=7), sync_token=None)
    assert tx.calendar_params[-1].get("showDeleted") == "true"


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
