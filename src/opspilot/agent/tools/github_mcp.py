"""GitHub MCP Ask tools — static names only (D-034)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from opspilot.integrations.github_mcp.client import call_pinned_tool
from opspilot.integrations.github_mcp.gate import github_mcp_gate_reason
from opspilot.llm.github_mcp_auth import OperatorGitHubMcpAuth
from opspilot.llm.prompt_safety import neutralize_text


def _pin_repo(args: dict[str, Any]) -> dict[str, Any]:
    import os

    owner = os.environ.get("OPSPILOT_GITHUB_MCP_OWNER", "").strip()
    repo = os.environ.get("OPSPILOT_GITHUB_MCP_REPO", "").strip()
    pinned = dict(args)
    pinned.pop("owner", None)
    pinned.pop("repo", None)
    if owner:
        pinned["owner"] = owner
    if repo:
        pinned["repo"] = repo
    return pinned


def _gated_call(
    tool: str,
    arguments: dict[str, Any],
    *,
    github_mcp_auth: OperatorGitHubMcpAuth | None,
) -> dict[str, Any]:
    reason = github_mcp_gate_reason(github_mcp_auth)
    if reason is not None:
        return {"ok": False, "error": reason}
    return call_pinned_tool(tool, arguments)


def run_get_me(
    *,
    session: Session,
    args: dict[str, Any],
    gmail_only: bool,
    operator_email: str | None,
    request_id: str | None,
    github_mcp_auth: OperatorGitHubMcpAuth | None = None,
) -> dict[str, Any]:
    del session, args, gmail_only, operator_email, request_id
    return _gated_call("get_me", {}, github_mcp_auth=github_mcp_auth)


def run_get_file_contents(
    *,
    session: Session,
    args: dict[str, Any],
    gmail_only: bool,
    operator_email: str | None,
    request_id: str | None,
    github_mcp_auth: OperatorGitHubMcpAuth | None = None,
) -> dict[str, Any]:
    del session, gmail_only, operator_email, request_id
    path = neutralize_text(str(args.get("path") or ""))[:512]
    if not path:
        return {"ok": False, "error": "missing_path"}
    payload: dict[str, Any] = {"path": path}
    ref = neutralize_text(str(args.get("ref") or "")).strip()
    if ref:
        payload["ref"] = ref[:128]
    result = _gated_call("get_file_contents", _pin_repo(payload), github_mcp_auth=github_mcp_auth)
    if result.get("ok"):
        result["path"] = path
    return result


def run_list_commits(
    *,
    session: Session,
    args: dict[str, Any],
    gmail_only: bool,
    operator_email: str | None,
    request_id: str | None,
    github_mcp_auth: OperatorGitHubMcpAuth | None = None,
) -> dict[str, Any]:
    del session, gmail_only, operator_email, request_id
    payload: dict[str, Any] = {}
    sha = neutralize_text(str(args.get("sha") or "")).strip()
    if sha:
        payload["sha"] = sha[:128]
    limit = args.get("limit")
    if limit is None:
        limit = 10
    payload["perPage"] = int(limit)
    result = _gated_call("list_commits", _pin_repo(payload), github_mcp_auth=github_mcp_auth)
    if result.get("ok") and isinstance(result.get("commits"), list) and limit is not None:
        result["commits"] = result["commits"][: int(limit)]
    return result


def run_pull_request_read(
    *,
    session: Session,
    args: dict[str, Any],
    gmail_only: bool,
    operator_email: str | None,
    request_id: str | None,
    github_mcp_auth: OperatorGitHubMcpAuth | None = None,
) -> dict[str, Any]:
    del session, gmail_only, operator_email, request_id
    try:
        number = int(args.get("pull_number") or args.get("pullNumber") or 0)
    except (TypeError, ValueError):
        return {"ok": False, "error": "invalid_pull_number"}
    if number <= 0:
        return {"ok": False, "error": "missing_pull_number"}
    payload = {"method": "get", "pullNumber": number}
    result = _gated_call("pull_request_read", _pin_repo(payload), github_mcp_auth=github_mcp_auth)
    if result.get("ok"):
        result["number"] = number
    return result
