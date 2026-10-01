"""Repository upsert idempotency (hermetic Postgres)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from opspilot.persistence.models import MeetingRow, WorkItemRow
from opspilot.persistence.repositories import meetings, oauth_credentials, sync_cursors, work_items


@pytest.fixture
def fernet_key(monkeypatch: pytest.MonkeyPatch) -> str:
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", key)
    return key


def test_work_item_upsert_by_provider_id_idempotent(db_session: Session) -> None:
    received = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)
    id1 = work_items.upsert_by_provider_id(
        db_session,
        provider_id="msg_abc",
        source_type="gmail",
        subject_or_title="Hello",
        body_or_description="Body one",
        sender_or_requester="a@example.com",
        received_at=received,
        thread_id="thr_1",
    )
    id2 = work_items.upsert_by_provider_id(
        db_session,
        provider_id="msg_abc",
        source_type="gmail",
        subject_or_title="Hello updated",
        body_or_description="Body two",
        sender_or_requester="a@example.com",
        received_at=received,
        thread_id="thr_1",
    )
    assert id1 == id2
    count = db_session.scalar(select(func.count()).select_from(WorkItemRow))
    assert count == 1
    row = db_session.scalars(select(WorkItemRow).where(WorkItemRow.provider_id == "msg_abc")).one()
    assert row.subject_or_title == "Hello updated"
    assert row.body_or_description == "Body two"


def test_meeting_upsert_idempotent(db_session: Session) -> None:
    start = datetime(2026, 9, 30, 15, 0, tzinfo=UTC)
    end = start + timedelta(hours=1)
    mid1 = meetings.upsert_by_provider_id(
        db_session,
        provider_id="evt_1",
        title="Standup",
        start_at=start,
        end_at=end,
    )
    mid2 = meetings.upsert_by_provider_id(
        db_session,
        provider_id="evt_1",
        title="Standup (updated)",
        start_at=start,
        end_at=end,
    )
    assert mid1 == mid2
    assert db_session.scalar(select(func.count()).select_from(MeetingRow)) == 1
    row = db_session.scalars(select(MeetingRow).where(MeetingRow.provider_id == "evt_1")).one()
    assert row.title == "Standup (updated)"


def test_sync_cursor_upsert(db_session: Session) -> None:
    sync_cursors.upsert_cursor(
        db_session,
        provider="google",
        account_email="demo@example.com",
        cursor_kind=sync_cursors.CURSOR_GMAIL_HISTORY,
        cursor_value="111",
    )
    sync_cursors.upsert_cursor(
        db_session,
        provider="google",
        account_email="demo@example.com",
        cursor_kind=sync_cursors.CURSOR_GMAIL_HISTORY,
        cursor_value="222",
    )
    assert (
        sync_cursors.get_cursor(
            db_session,
            provider="google",
            account_email="demo@example.com",
            cursor_kind=sync_cursors.CURSOR_GMAIL_HISTORY,
        )
        == "222"
    )


def test_oauth_credential_encrypt_round_trip(db_session: Session, fernet_key: str) -> None:
    _ = fernet_key
    oauth_credentials.upsert_encrypted_refresh(
        db_session,
        provider="google",
        account_email="demo@example.com",
        scopes=("https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/calendar.readonly"),
        refresh_token_plaintext="refresh-not-real",
    )
    got = oauth_credentials.get_decrypted_refresh(db_session, provider="google")
    assert got is not None
    email, token = got
    assert email == "demo@example.com"
    assert token == "refresh-not-real"
    assert oauth_credentials.is_connected(db_session, provider="google")


def test_is_connected_requires_gmail_and_calendar_scopes(db_session: Session, fernet_key: str) -> None:
    _ = fernet_key
    oauth_credentials.upsert_encrypted_refresh(
        db_session,
        provider="google",
        account_email="partial@example.com",
        scopes="openid email https://www.googleapis.com/auth/gmail.readonly",
        refresh_token_plaintext="refresh-partial",
    )
    assert oauth_credentials.is_connected(db_session, provider="google") is False
