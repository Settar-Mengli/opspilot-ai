"""get_calendar tool — list meetings in a window."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from opspilot.llm.prompt_safety import neutralize_text
from opspilot.persistence.repositories import meetings


def run(
    *,
    session: Session,
    args: dict[str, Any],
    gmail_only: bool,
    operator_email: str | None,
    request_id: str | None,
    github_mcp_auth: object | None = None,
) -> dict[str, Any]:
    del gmail_only, operator_email, request_id, github_mcp_auth
    now = datetime.now(UTC)
    days = min(int(args.get("days") or 7), 14)
    start = now - timedelta(days=1)
    end = now + timedelta(days=days)
    rows = meetings.list_in_range(session, start=start, end=end)
    items = [
        {
            "id": row.id,
            "title": neutralize_text(row.title)[:120],
            "start_at": row.start_at.isoformat(),
            "end_at": row.end_at.isoformat(),
        }
        for row in rows[:20]
    ]
    return {"ok": True, "meetings": items, "count": len(items)}
