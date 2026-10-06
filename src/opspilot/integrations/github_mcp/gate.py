"""Fail-closed GitHub MCP runtime gate (D-034). HTTP is forbidden until this returns None."""

from __future__ import annotations

import os

from opspilot.llm.github_mcp_auth import OperatorGitHubMcpAuth
from opspilot.services.operator_session import demo_mode_enabled

_TRUTHY = frozenset({"1", "true", "yes", "on"})


def github_mcp_enabled() -> bool:
    return os.environ.get("OPSPILOT_GITHUB_MCP_ENABLED", "").strip().lower() in _TRUTHY


def github_mcp_timeout_s() -> float:
    raw = os.environ.get("OPSPILOT_GITHUB_MCP_TIMEOUT_S", "15").strip()
    try:
        value = float(raw)
    except ValueError:
        return 15.0
    if value <= 0:
        return 15.0
    return min(value, 120.0)


def github_mcp_gate_reason(auth: OperatorGitHubMcpAuth | None) -> str | None:
    """Return a deny code, or None if a call may proceed to construct HTTP."""
    if os.environ.get("GITHUB_ACTIONS", "").strip().lower() in _TRUTHY | {"true"}:
        return "ci_blocked"
    if not github_mcp_enabled():
        return "mcp_disabled"
    if demo_mode_enabled():
        return "demo_mode"
    if auth is None or not isinstance(auth, OperatorGitHubMcpAuth) or auth.role != "demo_operator":
        return "operator_auth_required"
    if not os.environ.get("GITHUB_MCP_PAT", "").strip():
        return "missing_pat"
    if not os.environ.get("OPSPILOT_GITHUB_MCP_OWNER", "").strip():
        return "missing_owner"
    if not os.environ.get("OPSPILOT_GITHUB_MCP_REPO", "").strip():
        return "missing_repo"
    return None


def github_mcp_tools_unlocked(auth: OperatorGitHubMcpAuth | None) -> bool:
    """Ask allowlist may include the four MCP names (still no HTTP until gate_reason is None)."""
    if os.environ.get("GITHUB_ACTIONS", "").strip().lower() in _TRUTHY | {"true"}:
        return False
    if not github_mcp_enabled():
        return False
    if demo_mode_enabled():
        return False
    if auth is None or not isinstance(auth, OperatorGitHubMcpAuth) or auth.role != "demo_operator":
        return False
    return True
