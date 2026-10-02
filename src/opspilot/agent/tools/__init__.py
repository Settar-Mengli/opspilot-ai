"""Tool registry — allowlist only; send is never registered (D-031)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from opspilot.agent.tools import draft_reply, get_calendar, get_message, search_items

ToolFn = Callable[..., dict[str, Any]]

TOOL_REGISTRY: dict[str, ToolFn] = {
    "search_items": search_items.run,
    "get_message": get_message.run,
    "get_calendar": get_calendar.run,
    "draft_reply": draft_reply.run,
}


def assert_no_send_tools() -> None:
    for name in TOOL_REGISTRY:
        if "send" in name.lower():
            raise RuntimeError(f"send_tool_registered:{name}")


def execute_tool(
    name: str,
    args: dict[str, Any],
    *,
    session: Session,
    gmail_only: bool,
    operator_email: str | None,
    request_id: str | None,
) -> dict[str, Any]:
    assert_no_send_tools()
    fn = TOOL_REGISTRY.get(name)
    if fn is None:
        return {"ok": False, "error": f"unknown_tool:{name}"}
    return fn(
        session=session,
        args=args,
        gmail_only=gmail_only,
        operator_email=operator_email,
        request_id=request_id,
    )
