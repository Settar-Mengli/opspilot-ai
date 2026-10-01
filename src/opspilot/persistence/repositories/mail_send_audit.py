"""Mail send audit repository (D-033 / D-027)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
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
        created_at=datetime.now(UTC),
    )
    session.add(row)
    session.flush()
    return row
