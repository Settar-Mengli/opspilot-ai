"""search_items tool — filter work items (G7 aware)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import desc, select
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
    query = neutralize_text(str(args.get("query") or "")).lower()[:120]
    limit = min(int(args.get("limit") or 10), 20)
    stmt = select(WorkItemRow).order_by(desc(WorkItemRow.received_at)).limit(50)
    if gmail_only:
        stmt = stmt.where(WorkItemRow.source_type == "gmail")
    rows = list(session.scalars(stmt).all())
    matched: list[dict[str, str]] = []
    for row in rows:
        hay = f"{row.subject_or_title} {row.body_or_description} {row.sender_or_requester}".lower()
        if query and query not in hay:
            continue
        matched.append(
            {
                "id": row.id,
                "subject": neutralize_text(row.subject_or_title)[:120],
                "sender": neutralize_text(row.sender_or_requester)[:80],
                "source_type": row.source_type,
            }
        )
        if len(matched) >= limit:
            break
    return {"ok": True, "items": matched, "count": len(matched)}
