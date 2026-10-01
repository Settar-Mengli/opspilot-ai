"""HITL draft edit + approve + Gmail reply send (D-033)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from opspilot.integrations.gmail_client import GmailClient
from opspilot.integrations.google_http import GoogleHttpError, GoogleTransport, HttpxTransport, refresh_access_token
from opspilot.integrations.google_oauth import client_id, client_secret
from opspilot.persistence.repositories import mail_drafts, mail_send_audit, oauth_credentials
from opspilot.services.operator_session import demo_mode_enabled
from opspilot.services.send_allowlist import recipients_allowed

FORBIDDEN_EDIT_FIELDS = frozenset(
    {"to_addrs", "thread_id", "gmail_provider_id", "work_item_id", "id", "draft_id", "status"}
)


class MailHitlError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def edit_draft(
    session: Session,
    draft_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    bad = sorted(FORBIDDEN_EDIT_FIELDS.intersection(payload.keys()))
    if bad:
        raise MailHitlError("forbidden_edit_fields", f"Cannot edit fields: {', '.join(bad)}")
    allowed = {k: payload[k] for k in ("subject", "body") if k in payload}
    if set(payload.keys()) - set(allowed.keys()):
        extra = sorted(set(payload.keys()) - set(allowed.keys()))
        raise MailHitlError("unknown_edit_fields", f"Unknown fields: {', '.join(extra)}")
    if "subject" not in allowed or "body" not in allowed:
        raise MailHitlError("subject_body_required", "Edit requires subject and body.")
    draft = mail_drafts.get_draft(session, draft_id)
    if draft is None:
        raise MailHitlError("draft_not_found", "Draft not found.")
    if draft.status not in {"draft", "failed"}:
        raise MailHitlError("draft_not_editable", "Draft cannot be edited in this status.")
    mail_drafts.update_subject_body(session, draft, subject=str(allowed["subject"]), body=str(allowed["body"]))
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
        }

    draft = mail_drafts.get_draft(session, draft_id)
    if draft is None:
        raise MailHitlError("draft_not_found", "Draft not found.")
    if draft.payload_sha256 != expected_payload_sha256:
        raise MailHitlError("payload_hash_mismatch", "Draft changed; refresh and retry.")

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
        )
        raise MailHitlError("demo_mode_blocks_send", "DEMO_MODE blocks send.")

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
        )
        raise MailHitlError("recipient_not_allowlisted", "Recipient not on send allowlist.")

    cred = oauth_credentials.get_decrypted_refresh(session, provider="google")
    if cred is None:
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
    except GoogleHttpError as exc:
        raise MailHitlError("refresh_failed", "Google re-auth required.") from exc

    client = GmailClient(access_token=access, transport=tx)
    message_id = client.send_reply(
        thread_id=draft.thread_id,
        in_reply_to_provider_id=draft.gmail_provider_id,
        to_addrs=draft.to_addrs,
        subject=draft.subject,
        body=draft.body,
    )
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
