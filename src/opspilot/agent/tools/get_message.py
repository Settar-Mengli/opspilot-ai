"""get_message tool — fetch one work item."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from opspilot.llm.prompt_safety import neutralize_text
from opspilot.persistence.models import WorkItemRow


def run(
    *,
    session: Session,
    args: dict[str, Any],
    gmail_only: bool,
    operator_email: str | None,
    request_id: str | None,
    github_mcp_auth: object | None = None,
) -> dict[str, Any]:
    del operator_email, request_id, github_mcp_auth
    item_id = neutralize_text(str(args.get("id") or args.get("work_item_id") or ""))[:64]
    if not item_id:
        return {"ok": False, "error": "missing_id"}
    row = session.get(WorkItemRow, item_id)
    if row is None:
        return {"ok": False, "error": "not_found"}
    if gmail_only and row.source_type != "gmail":
        return {"ok": False, "error": "not_found"}
    return {
        "ok": True,
        "id": row.id,
        "subject": neutralize_text(row.subject_or_title)[:200],
        "body": neutralize_text(row.body_or_description)[:500],
        "sender": neutralize_text(row.sender_or_requester)[:120],
        "thread_id": row.thread_id or "",
        "provider_id": row.provider_id or "",
        "source_type": row.source_type,
    }
