"""Gmail deleted / trash / leave-INBOX removal on sync."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from cryptography.fernet import Fernet
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from opspilot.persistence.models import WorkItemRow
from opspilot.persistence.repositories import oauth_credentials, sync_cursors, work_items
from opspilot.services import google_sync


def _msg_json(mid: str, *, labels: list[str] | None = None) -> dict[str, Any]:
    return {
        "id": mid,
        "threadId": "thr",
        "labelIds": labels if labels is not None else ["INBOX"],
        "payload": {
            "headers": [
                {"name": "Subject", "value": f"Subj {mid}"},
                {"name": "From", "value": "x@example.com"},
                {"name": "Date", "value": "Tue, 30 Sep 2026 12:00:00 +0000"},
            ],
            "mimeType": "text/plain",
            "body": {"data": "Ym9keQ"},
        },
    }


class _HistoryTransport:
    def __init__(self, history: list[dict[str, Any]]) -> None:
        self.history = history
        self.calls: list[tuple[str, str, dict[str, Any] | None]] = []

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
        self.calls.append((method, url, params))
        if "oauth2.googleapis.com/token" in url:
            return httpx.Response(200, json={"access_token": "ya29.fake"})
        if url.endswith("/users/me/profile"):
            return httpx.Response(200, json={"historyId": "2000"})
        if "/users/me/history" in url:
            return httpx.Response(200, json={"history": self.history})
        if "/users/me/messages/" in url and not url.rstrip("/").endswith("/messages"):
            mid = url.rsplit("/", 1)[-1]
            return httpx.Response(200, json=_msg_json(mid, labels=["INBOX"]))
        if url.rstrip("/").endswith("/messages"):
            return httpx.Response(200, json={"messages": []})
        if "/calendars/primary/events" in url:
            return httpx.Response(200, json={"items": [], "nextSyncToken": "t"})
        return httpx.Response(500, json={"error": "unexpected"})


@pytest.fixture
def sync_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "csec")


def _seed(db_session: Session, provider_id: str) -> str:
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
    wid = work_items.upsert_by_provider_id(
        db_session,
        provider_id=provider_id,
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
    return wid


def test_sync_removes_deleted_gmail_messages(db_session: Session, sync_env: None) -> None:
    _seed(db_session, "gone_msg")
    tx = _HistoryTransport(
        [
            {"messagesDeleted": [{"message": {"id": "gone_msg"}}]},
            {"messagesAdded": [{"message": {"id": "new_msg"}}]},
        ]
    )
    result = google_sync.run_sync(db_session, transport=tx, providers=["gmail"])
    db_session.commit()
    assert result["gmail_removed"] == 1
    assert (
        db_session.scalar(select(func.count()).select_from(WorkItemRow).where(WorkItemRow.provider_id == "gone_msg"))
        == 0
    )
    assert (
        db_session.scalar(select(func.count()).select_from(WorkItemRow).where(WorkItemRow.provider_id == "new_msg"))
        == 1
    )
    hist_params = next(p for _m, u, p in tx.calls if "/history" in u)
    assert hist_params is not None
    assert "labelAdded" in hist_params["historyTypes"]
    assert "labelRemoved" in hist_params["historyTypes"]


def test_sync_removes_on_label_added_trash(db_session: Session, sync_env: None) -> None:
    _seed(db_session, "trash_msg")
    tx = _HistoryTransport([{"labelsAdded": [{"message": {"id": "trash_msg"}, "labelIds": ["TRASH"]}]}])
    result = google_sync.run_sync(db_session, transport=tx, providers=["gmail"])
    db_session.commit()
    assert result["gmail_removed"] == 1
    assert (
        db_session.scalar(select(func.count()).select_from(WorkItemRow).where(WorkItemRow.provider_id == "trash_msg"))
        == 0
    )


def test_sync_removes_on_label_removed_inbox(db_session: Session, sync_env: None) -> None:
    _seed(db_session, "archive_msg")
    tx = _HistoryTransport([{"labelsRemoved": [{"message": {"id": "archive_msg"}, "labelIds": ["INBOX"]}]}])
    result = google_sync.run_sync(db_session, transport=tx, providers=["gmail"])
    db_session.commit()
    assert result["gmail_removed"] == 1
    assert (
        db_session.scalar(select(func.count()).select_from(WorkItemRow).where(WorkItemRow.provider_id == "archive_msg"))
        == 0
    )


def test_full_sync_skips_trash_and_removes_local(db_session: Session, sync_env: None) -> None:
    _seed(db_session, "trash_local")

    class _FullTransport:
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
                return httpx.Response(404, json={"error": "expired"})
            if url.rstrip("/").endswith("/messages"):
                q = (params or {}).get("q") or ""
                if "trash" in str(q):
                    return httpx.Response(200, json={"messages": [{"id": "trash_local"}]})
                if "inbox" in str(q):
                    return httpx.Response(200, json={"messages": [{"id": "keep_inbox"}]})
                return httpx.Response(200, json={"messages": []})
            if "/users/me/messages/" in url:
                mid = url.rsplit("/", 1)[-1]
                labels = ["INBOX"] if mid == "keep_inbox" else ["TRASH"]
                return httpx.Response(200, json=_msg_json(mid, labels=labels))
            return httpx.Response(500, json={"error": "unexpected"})

    # Force full path via expired history (cursor present).
    result = google_sync.run_sync(db_session, transport=_FullTransport(), providers=["gmail"])
    db_session.commit()
    assert result["gmail_removed"] >= 1
    assert (
        db_session.scalar(select(func.count()).select_from(WorkItemRow).where(WorkItemRow.provider_id == "trash_local"))
        == 0
    )
    assert (
        db_session.scalar(select(func.count()).select_from(WorkItemRow).where(WorkItemRow.provider_id == "keep_inbox"))
        == 1
    )


def test_delete_by_provider_id_cascades_triage(db_session: Session, sync_env: None) -> None:
    wid = _seed(db_session, "triaged_gone")
    db_session.execute(
        text(
            """
            INSERT INTO runs (run_id, status, metadata_json, created_at)
            VALUES ('run_del_1', 'success', '{}'::jsonb, NOW())
            ON CONFLICT DO NOTHING
            """
        )
    )
    db_session.execute(
        text(
            """
            INSERT INTO triage_decisions (
              work_item_id, run_id, urgency, urgency_reason, category, category_reason,
              sentiment, sentiment_reason
            ) VALUES (
              :wid, 'run_del_1', 'low', 'r', 'other', 'r', 'neutral', 'r'
            )
            """
        ),
        {"wid": wid},
    )
    db_session.commit()
    assert work_items.delete_by_provider_id(db_session, provider_id="triaged_gone") is True
    db_session.commit()
    assert (
        db_session.scalar(
            select(func.count()).select_from(WorkItemRow).where(WorkItemRow.provider_id == "triaged_gone")
        )
        == 0
    )
    n = db_session.execute(
        text("SELECT count(*) FROM triage_decisions WHERE work_item_id = :wid"),
        {"wid": wid},
    ).scalar()
    assert n == 0
