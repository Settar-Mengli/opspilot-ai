"""Pinned GitHub MCP names and default remote URL (D-034)."""

from __future__ import annotations

PINNED_MCP_TOOLS: tuple[str, ...] = (
    "get_me",
    "get_file_contents",
    "list_commits",
    "pull_request_read",
)

WRITE_TOOL_DENY: frozenset[str] = frozenset(
    {
        "create_or_update_file",
        "push_files",
        "create_issue",
        "create_pull_request",
        "merge_pull_request",
        "update_issue",
        "add_issue_comment",
        "request_copilot_review",
        "create_branch",
        "delete_file",
        "fork_repository",
        "create_or_update_issue_comment",
        "update_pull_request",
        "merge_pull_request_merge",
        "create_pull_request_review",
        "submit_pending_pull_request_review",
        "add_comment_to_pending_review",
        "delete_pending_pull_request_review",
        "pull_request_review_write",
        "create_repository",
    }
)

COPILOT_GATED_HINTS: frozenset[str] = frozenset(
    {
        "copilot",
        "assign_copilot",
        "request_copilot",
        "create_pull_request_with_copilot",
    }
)

DEFAULT_MCP_URL = "https://api.githubcopilot.com/mcp/readonly"

# Owner C0 handshake 2026-10-06: remote spoke initialize-era 2025-11-25.
EXPECTED_PROTOCOL_VERSION = "2025-11-25"

X_MCP_TOOLS_HEADER = ",".join(PINNED_MCP_TOOLS)

HANDSHAKE_STDOUT_KEYS: frozenset[str] = frozenset(
    {
        "protocol_version",
        "session_id_issued",
        "tool_count",
        "tool_names",
        "allowlisted_present",
        "copilot_gated_advertised",
        "error",
    }
)

DEFAULT_TIMEOUT_S = 15.0
