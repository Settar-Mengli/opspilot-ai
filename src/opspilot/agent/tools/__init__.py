"""Tool registry — allowlist only; send is never registered (D-031 / D-034)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from opspilot.agent.tools import draft_reply, get_calendar, get_message, github_mcp, search_items
from opspilot.integrations.github_mcp.constants import WRITE_TOOL_DENY
from opspilot.llm.github_mcp_auth import OperatorGitHubMcpAuth

ToolFn = Callable[..., dict[str, Any]]

TOOL_REGISTRY: dict[str, ToolFn] = {
    "search_items": search_items.run,
    "get_message": get_message.run,
    "get_calendar": get_calendar.run,
    "draft_reply": draft_reply.run,
    "get_me": github_mcp.run_get_me,
    "get_file_contents": github_mcp.run_get_file_contents,
    "list_commits": github_mcp.run_list_commits,
    "pull_request_read": github_mcp.run_pull_request_read,
}


def assert_no_send_tools() -> None:
    for name in TOOL_REGISTRY:
        if "send" in name.lower():
            raise RuntimeError(f"send_tool_registered:{name}")


def assert_no_write_mcp_tools() -> None:
    for name in TOOL_REGISTRY:
        if name in WRITE_TOOL_DENY:
            raise RuntimeError(f"write_mcp_tool_registered:{name}")
        lowered = name.lower()
        if any(part in lowered for part in ("create_", "update_", "delete_", "push_", "merge_")):
            raise RuntimeError(f"write_mcp_tool_registered:{name}")


def execute_tool(
    name: str,
    args: dict[str, Any],
    *,
    session: Session,
    gmail_only: bool,
    operator_email: str | None,
    request_id: str | None,
    github_mcp_auth: OperatorGitHubMcpAuth | None = None,
) -> dict[str, Any]:
    assert_no_send_tools()
    assert_no_write_mcp_tools()
    fn = TOOL_REGISTRY.get(name)
    if fn is None:
        return {"ok": False, "error": f"unknown_tool:{name}"}
    return fn(
        session=session,
        args=args,
        gmail_only=gmail_only,
        operator_email=operator_email,
        request_id=request_id,
        github_mcp_auth=github_mcp_auth,
    )
