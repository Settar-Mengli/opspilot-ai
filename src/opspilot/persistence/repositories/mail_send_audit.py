"""Mail send audit repository (D-033 / D-027)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from opspilot.persistence.models import MailSendAuditRow


def get_by_idempotency_key(session: Session, key: str) -> MailSendAuditRow | None:
    return session.scalars(select(MailSendAuditRow).where(MailSendAuditRow.idempotency_key == key)).one_or_none()


def insert_audit(
    session: Session,
    *,
    draft_id: str | None,
    idempotency_key: str,
    to_addrs: str,
    payload_sha256: str,
    gmail_message_id: str | None = None,
    request_id: str | None = None,
    operator_email: str | None = None,
    demo_mode_blocked: bool = False,
    allowlist_denied: bool = False,
    send_failed: bool = False,
    error_code: str | None = None,
) -> MailSendAuditRow:
    row = MailSendAuditRow(
        draft_id=draft_id,
        idempotency_key=idempotency_key,
        to_addrs=to_addrs,
        payload_sha256=payload_sha256,
        gmail_message_id=gmail_message_id,
        request_id=request_id,
        operator_email=operator_email,
        demo_mode_blocked=demo_mode_blocked,
        allowlist_denied=allowlist_denied,
        send_failed=send_failed,
        error_code=(error_code[:64] if error_code else None),
        created_at=datetime.now(UTC),
    )
    session.add(row)
    session.flush()
    return row


def count_successful_sends_utc_day(session: Session, *, day_start: datetime) -> int:
    """Count cap-consuming sends since UTC day_start.

    Counts successful sends (gmail_message_id set, not blocked/failed) **or**
    ambiguous outcomes (error_code=send_outcome_unknown) so a possible-delivered
    message still consumes the daily budget (A1).
    """
    success = (
        MailSendAuditRow.gmail_message_id.is_not(None)
        & MailSendAuditRow.send_failed.is_(False)
        & MailSendAuditRow.demo_mode_blocked.is_(False)
        & MailSendAuditRow.allowlist_denied.is_(False)
    )
    unknown = MailSendAuditRow.error_code == "send_outcome_unknown"
    stmt = (
        select(func.count())
        .select_from(MailSendAuditRow)
        .where(MailSendAuditRow.created_at >= day_start)
        .where(or_(success, unknown))
    )
    return int(session.scalar(stmt) or 0)
