"""draft_reply tool — create mail_drafts only (no Gmail send)."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from opspilot.llm.prompt_safety import neutralize_text
from opspilot.persistence.models import WorkItemRow
from opspilot.persistence.repositories import mail_drafts
from opspilot.services.mail_address import MailAddressError, assert_safe_subject, parse_single_addr_spec

_RE_PREFIX = re.compile(r"(?i)^re:\s*")


def reply_subject_from_original(original: str | None) -> str:
    """Build a CR/LF-safe Re: subject without stacking Re: prefixes."""
    text = neutralize_text(str(original or "")).strip()
    while text and _RE_PREFIX.match(text):
        text = _RE_PREFIX.sub("", text, count=1).strip()
    if not text:
        text = "(no subject)"
    return assert_safe_subject(f"Re: {text[:490]}")


def run(
    *,
    session: Session,
    args: dict[str, Any],
    gmail_only: bool,
    operator_email: str | None,
    request_id: str | None,
    github_mcp_auth: object | None = None,
) -> dict[str, Any]:
    del github_mcp_auth
    item_id = neutralize_text(str(args.get("work_item_id") or args.get("id") or ""))[:64]
    # Model-supplied subject is ignored (D-031): server always derives Re: <original>.
    # Owner may edit subject later via HITL edit (D-033).
    body = neutralize_text(str(args.get("body") or ""))[:8000]
    if not item_id:
        return {"ok": False, "error": "missing_work_item_id"}
    if not body:
        return {"ok": False, "error": "missing_body"}
    row = session.get(WorkItemRow, item_id)
    if row is None:
        return {"ok": False, "error": "not_found"}
    if gmail_only and row.source_type != "gmail":
        return {"ok": False, "error": "not_found"}
    if not row.thread_id or not row.provider_id:
        return {"ok": False, "error": "missing_thread_or_provider"}
    try:
        subject = reply_subject_from_original(row.subject_or_title)
    except MailAddressError as exc:
        return {"ok": False, "error": exc.code}
    # Recipients server-derived from synced sender — never from model args.
    # Reply-to-self (sender == operator) is allowed at draft time; allowlist is approve/send (D-033).
    try:
        to_addrs = parse_single_addr_spec(row.sender_or_requester)
        subject = assert_safe_subject(subject)
    except MailAddressError as exc:
        return {"ok": False, "error": exc.code}
    # Ignore any model-supplied to_addrs / thread / provider.
    draft = mail_drafts.create_draft(
        session,
        work_item_id=row.id,
        thread_id=row.thread_id,
        gmail_provider_id=row.provider_id,
        to_addrs=to_addrs,
        subject=subject,
        body=body,
        operator_email=operator_email,
        request_id=request_id,
    )
    return {
        "ok": True,
        "draft_id": draft.id,
        "subject": draft.subject,
        "body": draft.body,
        "to_addrs": draft.to_addrs,
        "status": draft.status,
    }
