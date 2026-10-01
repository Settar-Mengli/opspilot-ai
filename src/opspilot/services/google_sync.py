"""Orchestrate Gmail + Calendar sync into Postgres (X1 idempotent)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from opspilot.integrations.calendar_client import CalendarClient
from opspilot.integrations.gmail_client import GmailClient
from opspilot.integrations.google_http import GoogleHttpError, GoogleTransport, HttpxTransport, refresh_access_token
from opspilot.integrations.google_oauth import client_id, client_secret
from opspilot.persistence.repositories import meetings, oauth_credentials, sync_cursors, work_items


class GoogleReauthRequired(RuntimeError):
    """Refresh token invalid or missing — operator must re-auth."""


def run_sync(
    session: Session,
    *,
    transport: GoogleTransport | None = None,
    providers: list[str] | None = None,
) -> dict[str, Any]:
    wanted = set(providers or ["gmail", "calendar"])
    cred = oauth_credentials.get_decrypted_refresh(session, provider="google")
    if cred is None:
        raise GoogleReauthRequired("no_google_credential")
    account_email, refresh = cred
    tx = transport or HttpxTransport()
    try:
        access = refresh_access_token(
            client_id=client_id(),
            client_secret=client_secret(),
            refresh_token=refresh,
            transport=tx,
        )
    except GoogleHttpError as exc:
        raise GoogleReauthRequired("refresh_failed") from exc

    result: dict[str, Any] = {
        "account_email": account_email,
        "gmail_upserted": 0,
        "calendar_upserted": 0,
    }
    if "gmail" in wanted:
        result["gmail_upserted"] = _sync_gmail(session, access_token=access, account_email=account_email, transport=tx)
    if "calendar" in wanted:
        result["calendar_upserted"] = _sync_calendar(
            session, access_token=access, account_email=account_email, transport=tx
        )
    return result


def _sync_gmail(
    session: Session,
    *,
    access_token: str,
    account_email: str,
    transport: GoogleTransport,
) -> int:
    client = GmailClient(access_token=access_token, transport=transport)
    cursor = sync_cursors.get_cursor(
        session,
        provider="google",
        account_email=account_email,
        cursor_kind=sync_cursors.CURSOR_GMAIL_HISTORY,
    )
    ids: list[str]
    deleted_ids: list[str] = []
    if cursor:
        hist = client.history_message_ids(start_history_id=cursor)
        if hist is None:
            ids = client.list_message_ids(max_results=50)
        else:
            ids, deleted_ids = hist
    else:
        ids = client.list_message_ids(max_results=50)

    for mid in deleted_ids:
        work_items.delete_by_provider_id(session, provider_id=mid)

    upserted = 0
    for mid in ids:
        msg = client.get_message(mid)
        if not msg.provider_id:
            continue
        work_items.upsert_by_provider_id(
            session,
            provider_id=msg.provider_id,
            source_type="gmail",
            subject_or_title=msg.subject,
            body_or_description=msg.body,
            sender_or_requester=msg.sender,
            received_at=msg.received_at,
            thread_id=msg.thread_id,
        )
        upserted += 1
    new_history = client.profile_history_id()
    sync_cursors.upsert_cursor(
        session,
        provider="google",
        account_email=account_email,
        cursor_kind=sync_cursors.CURSOR_GMAIL_HISTORY,
        cursor_value=new_history,
    )
    return upserted


def _sync_calendar(
    session: Session,
    *,
    access_token: str,
    account_email: str,
    transport: GoogleTransport,
) -> int:
    client = CalendarClient(access_token=access_token, transport=transport)
    now = datetime.now(UTC)
    time_min = now - timedelta(days=1)
    time_max = now + timedelta(days=7)
    sync_token = sync_cursors.get_cursor(
        session,
        provider="google",
        account_email=account_email,
        cursor_kind=sync_cursors.CURSOR_CALENDAR_SYNC,
    )
    events, next_token = client.list_events(time_min=time_min, time_max=time_max, sync_token=sync_token)
    if sync_token and next_token is None and not events:
        # 410 path: full window resync
        events, next_token = client.list_events(time_min=time_min, time_max=time_max, sync_token=None)
    upserted = 0
    for ev in events:
        if ev.cancelled:
            meetings.delete_by_provider_id(session, provider_id=ev.provider_id)
            continue
        if ev.start_at is None or ev.end_at is None:
            continue
        meetings.upsert_by_provider_id(
            session,
            provider_id=ev.provider_id,
            title=ev.title,
            start_at=ev.start_at,
            end_at=ev.end_at,
        )
        upserted += 1
    if next_token:
        sync_cursors.upsert_cursor(
            session,
            provider="google",
            account_email=account_email,
            cursor_kind=sync_cursors.CURSOR_CALENDAR_SYNC,
            cursor_value=next_token,
        )
    return upserted
