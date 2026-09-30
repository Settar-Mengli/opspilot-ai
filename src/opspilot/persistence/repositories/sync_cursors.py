"""Sync cursor repository (Gmail historyId / Calendar syncToken)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from opspilot.persistence.models import SyncCursorRow

CURSOR_GMAIL_HISTORY = "gmail_history_id"
CURSOR_CALENDAR_SYNC = "calendar_sync_token"


def get_cursor(
    session: Session,
    *,
    provider: str,
    account_email: str,
    cursor_kind: str,
) -> str | None:
    stmt = select(SyncCursorRow).where(
        SyncCursorRow.provider == provider,
        SyncCursorRow.account_email == account_email,
        SyncCursorRow.cursor_kind == cursor_kind,
    )
    row = session.scalars(stmt).one_or_none()
    return row.cursor_value if row is not None else None


def upsert_cursor(
    session: Session,
    *,
    provider: str,
    account_email: str,
    cursor_kind: str,
    cursor_value: str,
) -> None:
    now = datetime.now(UTC)
    stmt = pg_insert(SyncCursorRow).values(
        provider=provider,
        account_email=account_email,
        cursor_kind=cursor_kind,
        cursor_value=cursor_value,
        updated_at=now,
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_sync_cursors_provider_email_kind",
        set_={
            "cursor_value": stmt.excluded.cursor_value,
            "updated_at": stmt.excluded.updated_at,
        },
    )
    session.execute(stmt)
    session.flush()
