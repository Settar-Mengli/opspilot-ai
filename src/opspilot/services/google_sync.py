"""Orchestrate Gmail + Calendar sync into Postgres (X1 idempotent)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from opspilot.integrations.calendar_client import CalendarClient
from opspilot.integrations.gmail_client import GmailClient
from opspilot.integrations.google_http import GoogleHttpError, GoogleTransport, HttpxTransport, refresh_access_token
from opspilot.integrations.google_oauth import client_id, client_secret
from opspilot.persistence.repositories import meetings, oauth_credentials, sync_cursors, work_items

_logger = logging.getLogger("opspilot.sync.gmail")
_cal_logger = logging.getLogger("opspilot.sync.calendar")


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
        code = str(exc.args[0]) if exc.args else "refresh_failed"
        raise GoogleReauthRequired(code) from exc

    result: dict[str, Any] = {
        "account_email": account_email,
        "gmail_upserted": 0,
        "gmail_removed": 0,
        "calendar_upserted": 0,
    }
    if "gmail" in wanted:
        upserted, removed, gmail_truncated = _sync_gmail(
            session, access_token=access, account_email=account_email, transport=tx
        )
        result["gmail_upserted"] = upserted
        result["gmail_removed"] = removed
        result["gmail_truncated"] = gmail_truncated
    if "calendar" in wanted:
        cal_upserted, cal_truncated = _sync_calendar(
            session, access_token=access, account_email=account_email, transport=tx
        )
        result["calendar_upserted"] = cal_upserted
        result["calendar_truncated"] = cal_truncated
    from sqlalchemy import func, select

    from opspilot.persistence.models import MeetingRow, WorkItemRow

    result["gmail_total"] = int(
        session.scalar(select(func.count()).select_from(WorkItemRow).where(WorkItemRow.source_type == "gmail")) or 0
    )
    result["meetings_total"] = int(session.scalar(select(func.count()).select_from(MeetingRow)) or 0)
    return result


def _sync_gmail(
    session: Session,
    *,
    access_token: str,
    account_email: str,
    transport: GoogleTransport,
) -> tuple[int, int, bool]:
    client = GmailClient(access_token=access_token, transport=transport)
    cursor = sync_cursors.get_cursor(
        session,
        provider="google",
        account_email=account_email,
        cursor_kind=sync_cursors.CURSOR_GMAIL_HISTORY,
    )
    ids: list[str]
    removed_ids: list[str] = []
    mode = "full"
    history_truncated = False
    list_truncated = False
    last_hist_id: str | None = None
    if cursor:
        hist = client.history_message_ids(start_history_id=cursor)
        if hist is None:
            mode = "full_resync"
            ids, list_truncated = client.list_message_ids(max_results=50, query="in:inbox")
            trash_ids, trash_trunc = client.list_message_ids(max_results=50, query="in:trash")
            removed_ids = trash_ids
            list_truncated = list_truncated or trash_trunc
        else:
            mode = "incremental"
            ids, removed_ids, history_truncated, last_hist_id = hist
            if history_truncated and not last_hist_id:
                # Truncate without usable history id — fall back to full list (C3).
                mode = "full_resync_after_truncate"
                history_truncated = False
                ids, list_truncated = client.list_message_ids(max_results=50, query="in:inbox")
                trash_ids, trash_trunc = client.list_message_ids(max_results=50, query="in:trash")
                removed_ids = trash_ids
                list_truncated = list_truncated or trash_trunc
    else:
        ids, list_truncated = client.list_message_ids(max_results=50, query="in:inbox")
        trash_ids, trash_trunc = client.list_message_ids(max_results=50, query="in:trash")
        removed_ids = trash_ids
        list_truncated = list_truncated or trash_trunc

    # Deduplicate while preserving order.
    seen_rm: set[str] = set()
    uniq_removed: list[str] = []
    for mid in removed_ids:
        if mid not in seen_rm:
            seen_rm.add(mid)
            uniq_removed.append(mid)

    removed = 0
    for mid in uniq_removed:
        if work_items.delete_by_provider_id(session, provider_id=mid):
            removed += 1

    upserted = 0
    skipped_non_inbox = 0
    for mid in ids:
        if mid in seen_rm:
            continue
        try:
            msg = client.get_message(mid)
        except GoogleHttpError as exc:
            # History/list can reference ids already gone (trash/expunge race) — skip/remove.
            if exc.status_code == 404:
                if work_items.delete_by_provider_id(session, provider_id=mid):
                    removed += 1
                continue
            raise
        if not msg.provider_id:
            continue
        labels = set(msg.label_ids)
        if "TRASH" in labels or "INBOX" not in labels:
            skipped_non_inbox += 1
            if work_items.delete_by_provider_id(session, provider_id=mid):
                removed += 1
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

    # Cursor safety: never advance past unprocessed history pages.
    history_end = "-"
    gmail_truncated = False
    if history_truncated:
        if last_hist_id:
            sync_cursors.upsert_cursor(
                session,
                provider="google",
                account_email=account_email,
                cursor_kind=sync_cursors.CURSOR_GMAIL_HISTORY,
                cursor_value=last_hist_id,
            )
            history_end = last_hist_id
        else:
            # Keep prior cursor unchanged so the next sync re-reads from the same start.
            history_end = cursor or "-"
        _logger.info(
            "gmail_sync cursor_held truncated=1 last_hid=%s prior=%s",
            last_hist_id or "-",
            cursor or "-",
        )
    elif list_truncated:
        # Full-list incomplete: do not claim a complete profile history id (A5).
        gmail_truncated = True
        history_end = cursor or "-"
        _logger.warning(
            "gmail_sync list_truncated=1 upserted=%s removed_local=%s prior_cursor_kept=%s",
            upserted,
            removed,
            "1" if cursor else "0",
        )
    else:
        new_history = client.profile_history_id()
        sync_cursors.upsert_cursor(
            session,
            provider="google",
            account_email=account_email,
            cursor_kind=sync_cursors.CURSOR_GMAIL_HISTORY,
            cursor_value=new_history,
        )
        history_end = new_history

    _logger.info(
        "gmail_sync mode=%s history_start=%s added_candidates=%s removed_candidates=%s "
        "upserted=%s removed_local=%s skipped_non_inbox=%s history_end=%s "
        "history_truncated=%s list_truncated=%s gmail_truncated=%s",
        mode,
        cursor or "-",
        len(ids),
        len(uniq_removed),
        upserted,
        removed,
        skipped_non_inbox,
        history_end,
        int(history_truncated),
        int(list_truncated),
        int(gmail_truncated),
    )
    return upserted, removed, gmail_truncated


def _sync_calendar(
    session: Session,
    *,
    access_token: str,
    account_email: str,
    transport: GoogleTransport,
) -> tuple[int, bool]:
    client = CalendarClient(access_token=access_token, transport=transport)
    now = datetime.now(UTC)
    # Same bounds for API list and absence reconcile — must not diverge.
    time_min = now - timedelta(days=1)
    time_max = now + timedelta(days=7)
    sync_token = sync_cursors.get_cursor(
        session,
        provider="google",
        account_email=account_email,
        cursor_kind=sync_cursors.CURSOR_CALENDAR_SYNC,
    )
    full_window = sync_token is None
    listed = client.list_events(time_min=time_min, time_max=time_max, sync_token=sync_token)
    if listed.gone:
        # 410 path: full window resync
        full_window = True
        listed = client.list_events(time_min=time_min, time_max=time_max, sync_token=None)
    events = listed.events
    upserted = 0
    seen_ids: set[str] = set()
    for ev in events:
        seen_ids.add(ev.provider_id)
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

    calendar_truncated = bool(listed.truncated)
    if listed.truncated:
        # Never keep a syncToken after truncate — Google restarts at page 1 under the same token.
        sync_cursors.delete_cursor(
            session,
            provider="google",
            account_email=account_email,
            cursor_kind=sync_cursors.CURSOR_CALENDAR_SYNC,
        )
        _cal_logger.warning(
            "calendar_sync truncated=1 events=%s upserted=%s full_window=%s",
            len(events),
            upserted,
            int(full_window),
        )
    elif listed.next_sync_token:
        sync_cursors.upsert_cursor(
            session,
            provider="google",
            account_email=account_email,
            cursor_kind=sync_cursors.CURSOR_CALENDAR_SYNC,
            cursor_value=listed.next_sync_token,
        )
        if full_window:
            # Absence reconcile: hard-deleted / moved-out events are not returned.
            removed_absent = 0
            for row in meetings.list_starting_in_window(session, time_min=time_min, time_max=time_max):
                if row.provider_id not in seen_ids:
                    if meetings.delete_by_provider_id(session, provider_id=row.provider_id):
                        removed_absent += 1
            if removed_absent:
                _cal_logger.info("calendar_sync absence_removed=%s", removed_absent)
    return upserted, calendar_truncated
