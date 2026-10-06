"""JSON-emulated agent turn schema + parse helpers (D-031 / D-034)."""

from __future__ import annotations

from typing import Any, Literal, Self

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator

from opspilot.integrations.github_mcp.constants import PINNED_MCP_TOOLS
from opspilot.integrations.github_mcp.gate import github_mcp_tools_unlocked
from opspilot.llm.github_mcp_auth import OperatorGitHubMcpAuth

CORE_TOOLS = frozenset({"search_items", "get_message", "get_calendar", "draft_reply"})
MCP_TOOLS = frozenset(PINNED_MCP_TOOLS)
ALLOWED_TOOLS = CORE_TOOLS

TOOL_ERROR_HINTS: dict[str, str] = {
    "not_found": "use the exact id from search_items or get_message",
    "missing_work_item_id": "work_item_id (or id) is required",
    "missing_id": "id is required",
    "missing_body": "body is required",
    "missing_subject_or_body": "body is required",
    "missing_thread_or_provider": "work item is missing thread or provider id",
    "empty_address": "synced sender address is empty",
    "invalid_address": "synced sender address is invalid",
    "unsafe_subject": "subject contains unsafe characters",
    "unsafe_address_chars": "synced sender address has unsafe characters",
    "multiple_addresses": "synced sender must be a single address",
    "mcp_timeout": "retry the same GitHub read",
    "mcp_tool_error": "GitHub MCP tool returned an error",
    "mcp_protocol_error": "GitHub MCP protocol error",
    "mcp_protocol_version_mismatch": "GitHub MCP protocol version changed; operator must re-run handshake",
    "mcp_http_4xx": "GitHub MCP HTTP client error; check operator auth and flag",
    "mcp_http_5xx": "GitHub MCP HTTP server error; retry later",
    "mcp_http_error": "GitHub MCP HTTP error",
    "mcp_disabled": "GitHub MCP is off",
    "missing_path": "path is required",
    "missing_pull_number": "pull_number is required",
    "invalid_pull_number": "pull_number must be a positive integer",
    "ci_blocked": "GitHub MCP is not available",
    "operator_auth_required": "GitHub MCP requires an operator session",
    "demo_mode": "GitHub MCP is disabled in demo mode",
    "missing_pat": "GitHub MCP is not configured",
    "missing_owner": "GitHub MCP is not configured",
    "missing_repo": "GitHub MCP is not configured",
}


def tool_error_hint(code: str | None) -> str | None:
    """Short trusted, content-free recovery hint for a tool error code."""
    if not code:
        return None
    return TOOL_ERROR_HINTS.get(str(code).strip())


def allowed_tools(*, github_mcp_auth: OperatorGitHubMcpAuth | None = None) -> frozenset[str]:
    if github_mcp_tools_unlocked(github_mcp_auth):
        return CORE_TOOLS | MCP_TOOLS
    return CORE_TOOLS


def tool_system_fragment(*, github_mcp_auth: OperatorGitHubMcpAuth | None = None) -> str:
    names = ", ".join(sorted(allowed_tools(github_mcp_auth=github_mcp_auth)))
    extra = ""
    if github_mcp_tools_unlocked(github_mcp_auth):
        extra = (
            " GitHub MCP (read-only, this repo only): get_me:{}; "
            "get_file_contents:{path:string, ref?:string}; "
            "list_commits:{sha?:string, limit?:int<=20}; "
            "pull_request_read:{pull_number:int}. "
            "Never invent owner/repo; the server pins the repository. "
            "Never call tools that are not listed."
        )
    return (
        "You are OpsPilot. Respond with a single JSON object matching the schema: "
        '{"kind":"tool","tool":"<name>","args":{...}} or {"kind":"final","final":"<answer>"}. '
        f"Allowed tools: {names}. "
        "Tool args: "
        "search_items:{query:string,limit?:int<=20}; "
        "get_message:{id:string}; "
        "get_calendar:{days?:int<=14}; "
        "draft_reply:{work_item_id|id:string, body:string, subject?:string}. "
        "draft_reply.subject from the model is ignored; server sets Re: <original>. "
        "draft_reply.work_item_id must be the exact `id` from search_items/get_message "
        "or the triage context — never a Gmail provider/thread id. "
        "Examples (placeholder ids only): "
        '{"kind":"tool","tool":"search_items","args":{"query":"project sync","limit":5}}; '
        '{"kind":"tool","tool":"draft_reply","args":{"work_item_id":"<exact id from search_items>",'
        '"body":"..."}}. '
        "Never invent a send tool. Under 200 words for final."
        f"{extra}"
    )


TOOL_SYSTEM_FRAGMENT = tool_system_fragment()


class AgentTurn(BaseModel):
    """One model turn: either a tool call or a final answer."""

    kind: Literal["tool", "final"]
    tool: str | None = None
    args: dict[str, Any] = Field(default_factory=dict)
    final: str | None = None

    @field_validator("tool")
    @classmethod
    def _tool_allowlisted(cls, value: str | None, info: ValidationInfo) -> str | None:
        if value is None:
            return value
        allowed = CORE_TOOLS
        ctx = info.context or {}
        raw = ctx.get("allowed_tools")
        if isinstance(raw, frozenset | set):
            allowed = frozenset(str(item) for item in raw)
        if value not in allowed:
            raise ValueError(f"tool_not_allowlisted:{value}")
        return value

    @model_validator(mode="after")
    def _kind_fields(self) -> Self:
        if self.kind == "tool":
            if not self.tool:
                raise ValueError("tool_required")
        elif self.kind == "final":
            if not (self.final and self.final.strip()):
                raise ValueError("final_required")
        return self
