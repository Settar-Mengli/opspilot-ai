"""Gmail history.list params + stale historyId full-resync fallback."""

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


class _HistoryParamTransport:
    """Captures history params; returns 400 until types are a proper list."""

    def __init__(self) -> None:
        self.history_params: list[dict[str, Any]] = []
        self.list_calls = 0

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
            return httpx.Response(200, json={"historyId": "3000"})
        if "/users/me/history" in url:
            p = dict(params or {})
            self.history_params.append(p)
            types = p.get("historyTypes")
            # Simulate Gmail: comma-joined string → 400; proper list → 200.
            if isinstance(types, str) and "," in types:
                return httpx.Response(400, json={"error": {"code": 400, "message": "Invalid historyTypes"}})
            if types == ["messageAdded", "messageDeleted"] or (
                isinstance(types, list) and set(types) == {"messageAdded", "messageDeleted"}
            ):
                return httpx.Response(200, json={"history": []})
            return httpx.Response(400, json={"error": {"code": 400, "message": "bad historyTypes"}})
        if url.endswith("/users/me/messages"):
            self.list_calls += 1
            return httpx.Response(200, json={"messages": [{"id": "listed_1"}]})
        if "/users/me/messages/" in url:
            mid = url.rsplit("/", 1)[-1]
            return httpx.Response(
                200,
                json={
                    "id": mid,
                    "threadId": "thr",
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


class _StaleHistoryTransport:
    """history 400 (invalid startHistoryId) → full list resync."""

    def __init__(self) -> None:
        self.list_calls = 0

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
            return httpx.Response(200, json={"historyId": "4000"})
        if "/users/me/history" in url:
            return httpx.Response(400, json={"error": {"code": 400, "message": "Invalid startHistoryId"}})
        if url.endswith("/users/me/messages"):
            self.list_calls += 1
            return httpx.Response(200, json={"messages": [{"id": "full_resync_1"}]})
        if "/users/me/messages/" in url:
            mid = url.rsplit("/", 1)[-1]
            return httpx.Response(
                200,
                json={
                    "id": mid,
                    "threadId": "thr",
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


def _seed_cursor(db_session: Session) -> None:
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


def test_history_types_sent_as_list_not_csv(db_session: Session, sync_env: None) -> None:
    _seed_cursor(db_session)
    tx = _HistoryParamTransport()
    google_sync.run_sync(db_session, transport=tx, providers=["gmail"])
    assert tx.history_params, "expected history.list call"
    types = tx.history_params[0].get("historyTypes")
    assert types == ["messageAdded", "messageDeleted"]
    assert not isinstance(types, str)


def test_history_400_falls_back_to_full_list_resync(db_session: Session, sync_env: None) -> None:
    _seed_cursor(db_session)
    tx = _StaleHistoryTransport()
    result = google_sync.run_sync(db_session, transport=tx, providers=["gmail"])
    db_session.commit()
    assert tx.list_calls == 1
    assert result["gmail_upserted"] == 1
    assert (
        db_session.scalar(
            select(func.count()).select_from(WorkItemRow).where(WorkItemRow.provider_id == "full_resync_1")
        )
        == 1
    )
