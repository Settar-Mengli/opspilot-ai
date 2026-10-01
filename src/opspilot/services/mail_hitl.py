"""HITL draft edit + approve + Gmail reply send (D-033)."""

from __future__ import annotations

import hashlib
import os
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from opspilot.integrations.gmail_client import GmailClient
from opspilot.integrations.google_http import GoogleHttpError, GoogleTransport, HttpxTransport, refresh_access_token
from opspilot.integrations.google_oauth import client_id, client_secret
from opspilot.persistence.repositories import mail_drafts, mail_send_audit, oauth_credentials
from opspilot.services.mail_address import MailAddressError, assert_safe_subject, parse_single_addr_spec
from opspilot.services.operator_session import demo_mode_enabled
from opspilot.services.send_allowlist import recipients_allowed

FORBIDDEN_EDIT_FIELDS = frozenset(
    {
        "to_addrs",
        "thread_id",
        "gmail_provider_id",
        "work_item_id",
        "id",
        "draft_id",
        "status",
        "payload_sha256",
        "operator_email",
        "request_id",
    }
)


class MailHitlError(RuntimeError):
    def __init__(self, code: str, message: str, *, http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


def _send_day_lock_key(day_start: datetime) -> int:
    """Stable signed 63-bit advisory lock key for UTC send-cap day."""
    digest = hashlib.sha256(f"opspilot_send_cap:{day_start.date().isoformat()}".encode()).digest()
    return int.from_bytes(digest[:8], "big") & 0x7FFFFFFFFFFFFFFF


def _acquire_send_cap_lock(session: Session, day_start: datetime) -> None:
    """Transaction-scoped advisory lock; released on commit/rollback."""
    session.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _send_day_lock_key(day_start)})


def _send_max_per_day() -> int:
    raw = os.environ.get("OPSPILOT_SEND_MAX_PER_DAY", "5").strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return 5


def _utc_day_start() -> datetime:
    now = datetime.now(UTC)
    return datetime(now.year, now.month, now.day, tzinfo=UTC)


def _require_owner(draft: Any, operator_email: str) -> None:
    owned = (draft.operator_email or "").strip().lower()
    if not owned or owned != operator_email.strip().lower():
        raise MailHitlError("draft_owner_mismatch", "Draft not owned by operator.", http_status=403)


def edit_draft(
    session: Session,
    draft_id: str,
    payload: dict[str, Any],
    *,
    operator_email: str,
) -> dict[str, Any]:
    bad = sorted(FORBIDDEN_EDIT_FIELDS.intersection(payload.keys()))
    if bad:
        raise MailHitlError("forbidden_edit_fields", "Cannot edit reserved fields.", http_status=422)
    allowed = {k: payload[k] for k in ("subject", "body") if k in payload}
    if set(payload.keys()) - set(allowed.keys()):
        raise MailHitlError("unknown_edit_fields", "Unknown fields.", http_status=422)
    if "subject" not in allowed or "body" not in allowed:
        raise MailHitlError("subject_body_required", "Edit requires subject and body.")
    try:
        subject = assert_safe_subject(str(allowed["subject"]))
    except MailAddressError as exc:
        raise MailHitlError(exc.code, "Invalid subject.", http_status=422) from exc
    body = str(allowed["body"])
    draft = mail_drafts.get_draft(session, draft_id)
    if draft is None:
        raise MailHitlError("draft_not_found", "Draft not found.", http_status=404)
    _require_owner(draft, operator_email)
    if draft.status != "draft":
        raise MailHitlError("draft_not_editable", "Draft cannot be edited in this status.", http_status=409)
    mail_drafts.update_subject_body(session, draft, subject=subject, body=body)
    return {
        "id": draft.id,
        "subject": draft.subject,
        "body": draft.body,
        "to_addrs": draft.to_addrs,
        "payload_sha256": draft.payload_sha256,
        "status": draft.status,
    }


def approve_and_send(
    session: Session,
    draft_id: str,
    *,
    expected_payload_sha256: str,
    operator_email: str,
    request_id: str | None,
    idempotency_key: str | None = None,
    transport: GoogleTransport | None = None,
) -> dict[str, Any]:
    key = (idempotency_key or "").strip() or f"send-{uuid.uuid4().hex}"
    existing = mail_send_audit.get_by_idempotency_key(session, key)
    if existing is not None:
        return {
            "status": "idempotent_replay",
            "audit_id": existing.id,
            "gmail_message_id": existing.gmail_message_id,
            "demo_mode_blocked": existing.demo_mode_blocked,
            "allowlist_denied": existing.allowlist_denied,
            "send_failed": existing.send_failed,
        }

    draft = mail_drafts.get_draft(session, draft_id)
    if draft is None:
        raise MailHitlError("draft_not_found", "Draft not found.", http_status=404)
    _require_owner(draft, operator_email)
    if draft.status != "draft":
        raise MailHitlError("draft_not_approvable", "Draft cannot be approved in this status.", http_status=409)
    if draft.payload_sha256 != expected_payload_sha256:
        raise MailHitlError("payload_hash_mismatch", "Draft changed; refresh and retry.")

    try:
        parse_single_addr_spec(draft.to_addrs)
        assert_safe_subject(draft.subject)
    except MailAddressError as exc:
        raise MailHitlError(exc.code, "Invalid draft addressing.", http_status=400) from exc

    if demo_mode_enabled():
        mail_send_audit.insert_audit(
            session,
            draft_id=draft.id,
            idempotency_key=key,
            to_addrs=draft.to_addrs,
            payload_sha256=draft.payload_sha256,
            request_id=request_id,
            operator_email=operator_email,
            demo_mode_blocked=True,
            error_code="demo_mode_blocks_send",
        )
        raise MailHitlError("demo_mode_blocks_send", "DEMO_MODE blocks send.", http_status=403)

    if not recipients_allowed(draft.to_addrs):
        mail_send_audit.insert_audit(
            session,
            draft_id=draft.id,
            idempotency_key=key,
            to_addrs=draft.to_addrs,
            payload_sha256=draft.payload_sha256,
            request_id=request_id,
            operator_email=operator_email,
            allowlist_denied=True,
            error_code="recipient_not_allowlisted",
        )
        raise MailHitlError("recipient_not_allowlisted", "Recipient not on send allowlist.", http_status=403)

    max_day = _send_max_per_day()
    day_start = _utc_day_start()
    _acquire_send_cap_lock(session, day_start)
    sent_today = mail_send_audit.count_successful_sends_utc_day(session, day_start=day_start)
    if sent_today >= max_day:
        mail_send_audit.insert_audit(
            session,
            draft_id=draft.id,
            idempotency_key=key,
            to_addrs=draft.to_addrs,
            payload_sha256=draft.payload_sha256,
            request_id=request_id,
            operator_email=operator_email,
            send_failed=True,
            error_code="send_daily_cap",
        )
        raise MailHitlError("send_daily_cap", "Daily send cap reached.", http_status=429)

    claimed = mail_drafts.claim_for_approve(session, draft_id)
    if claimed is None:
        raise MailHitlError("draft_already_claimed", "Draft already approved or sent.", http_status=409)
    draft = claimed

    cred = oauth_credentials.get_decrypted_refresh(session, provider="google")
    if cred is None:
        mail_drafts.set_status(session, draft, "failed")
        mail_send_audit.insert_audit(
            session,
            draft_id=draft.id,
            idempotency_key=key,
            to_addrs=draft.to_addrs,
            payload_sha256=draft.payload_sha256,
            request_id=request_id,
            operator_email=operator_email,
            send_failed=True,
            error_code="no_google_credential",
        )
        raise MailHitlError("no_google_credential", "Google not connected.")
    _email, refresh = cred
    tx = transport or HttpxTransport()
    try:
        access = refresh_access_token(
            client_id=client_id(),
            client_secret=client_secret(),
            refresh_token=refresh,
            transport=tx,
        )
    except GoogleHttpError:
        mail_drafts.set_status(session, draft, "failed")
        mail_send_audit.insert_audit(
            session,
            draft_id=draft.id,
            idempotency_key=key,
            to_addrs=draft.to_addrs,
            payload_sha256=draft.payload_sha256,
            request_id=request_id,
            operator_email=operator_email,
            send_failed=True,
            error_code="refresh_failed",
        )
        raise MailHitlError("refresh_failed", "Google re-auth required.") from None

    client = GmailClient(access_token=access, transport=tx)
    try:
        message_id = client.send_reply(
            thread_id=draft.thread_id,
            in_reply_to_provider_id=draft.gmail_provider_id,
            to_addrs=draft.to_addrs,
            subject=draft.subject,
            body=draft.body,
        )
    except GoogleHttpError as exc:
        code = str(exc.args[0] if exc.args else "gmail_send_failed")[:64]
        mail_drafts.set_status(session, draft, "failed")
        mail_send_audit.insert_audit(
            session,
            draft_id=draft.id,
            idempotency_key=key,
            to_addrs=draft.to_addrs,
            payload_sha256=draft.payload_sha256,
            request_id=request_id,
            operator_email=operator_email,
            send_failed=True,
            error_code=code,
        )
        raise MailHitlError("gmail_send_failed", "Send failed.") from None

    mail_drafts.set_status(session, draft, "sent")
    audit = mail_send_audit.insert_audit(
        session,
        draft_id=draft.id,
        idempotency_key=key,
        to_addrs=draft.to_addrs,
        payload_sha256=draft.payload_sha256,
        gmail_message_id=message_id,
        request_id=request_id,
        operator_email=operator_email,
    )
    return {
        "status": "sent",
        "audit_id": audit.id,
        "gmail_message_id": message_id,
        "draft_id": draft.id,
    }
