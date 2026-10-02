"""Mail draft repository (HITL reply drafts, D-033)."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from opspilot.persistence.models import MailDraftRow

DRAFT_STATUSES = frozenset({"draft", "approved", "sent", "cancelled", "failed"})


def new_draft_id() -> str:
    return f"md_{uuid4().hex}"


def compute_payload_sha256(
    *,
    work_item_id: str | None,
    thread_id: str,
    gmail_provider_id: str,
    to_addrs: str,
    subject: str,
    body: str,
) -> str:
    """Exact-payload hash over server-owned identity + editable subject/body."""
    canonical = "\n".join(
        [
            work_item_id or "",
            thread_id,
            gmail_provider_id,
            to_addrs,
            subject,
            body,
        ]
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def create_draft(
    session: Session,
    *,
    work_item_id: str | None,
    thread_id: str,
    gmail_provider_id: str,
    to_addrs: str,
    subject: str,
    body: str,
    operator_email: str | None = None,
    request_id: str | None = None,
) -> MailDraftRow:
    now = datetime.now(UTC)
    payload = compute_payload_sha256(
        work_item_id=work_item_id,
        thread_id=thread_id,
        gmail_provider_id=gmail_provider_id,
        to_addrs=to_addrs,
        subject=subject,
        body=body,
    )
    row = MailDraftRow(
        id=new_draft_id(),
        work_item_id=work_item_id,
        thread_id=thread_id,
        gmail_provider_id=gmail_provider_id,
        to_addrs=to_addrs,
        subject=subject,
        body=body,
        payload_sha256=payload,
        status="draft",
        operator_email=operator_email,
        request_id=request_id,
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    session.flush()
    return row


def get_draft(session: Session, draft_id: str) -> MailDraftRow | None:
    return session.get(MailDraftRow, draft_id)


def update_subject_body(
    session: Session,
    draft: MailDraftRow,
    *,
    subject: str,
    body: str,
) -> MailDraftRow:
    draft.subject = subject
    draft.body = body
    draft.payload_sha256 = compute_payload_sha256(
        work_item_id=draft.work_item_id,
        thread_id=draft.thread_id,
        gmail_provider_id=draft.gmail_provider_id,
        to_addrs=draft.to_addrs,
        subject=subject,
        body=body,
    )
    draft.updated_at = datetime.now(UTC)
    session.flush()
    return draft


def set_status(session: Session, draft: MailDraftRow, status: str) -> MailDraftRow:
    if status not in DRAFT_STATUSES:
        raise ValueError(f"invalid_draft_status:{status}")
    draft.status = status
    draft.updated_at = datetime.now(UTC)
    session.flush()
    return draft


def claim_for_approve(session: Session, draft_id: str) -> MailDraftRow | None:
    """Atomic draft→approved transition. Returns row if claimed, else None."""
    now = datetime.now(UTC)
    result = session.execute(
        update(MailDraftRow)
        .where(MailDraftRow.id == draft_id)
        .where(MailDraftRow.status == "draft")
        .values(status="approved", updated_at=now)
        .returning(MailDraftRow.id)
    )
    claimed_id = result.scalar_one_or_none()
    session.flush()
    if claimed_id is None:
        return None
    return session.get(MailDraftRow, claimed_id)


def list_by_status(session: Session, status: str, *, limit: int = 50) -> list[MailDraftRow]:
    stmt = (
        select(MailDraftRow).where(MailDraftRow.status == status).order_by(MailDraftRow.created_at.desc()).limit(limit)
    )
    return list(session.scalars(stmt).all())
