"""JSON-emulated agent turn schema + parse helpers (D-031)."""

from __future__ import annotations

from typing import Any, Literal, Self

from pydantic import BaseModel, Field, field_validator, model_validator

ALLOWED_TOOLS = frozenset({"search_items", "get_message", "get_calendar", "draft_reply"})

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
}


def tool_error_hint(code: str | None) -> str | None:
    """Short trusted, content-free recovery hint for a tool error code."""
    if not code:
        return None
    return TOOL_ERROR_HINTS.get(str(code).strip())


class AgentTurn(BaseModel):
    """One model turn: either a tool call or a final answer."""

    kind: Literal["tool", "final"]
    tool: str | None = None
    args: dict[str, Any] = Field(default_factory=dict)
    final: str | None = None

    @field_validator("tool")
    @classmethod
    def _tool_allowlisted(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if value not in ALLOWED_TOOLS:
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


TOOL_SYSTEM_FRAGMENT = (
    "You are OpsPilot. Respond with a single JSON object matching the schema: "
    '{"kind":"tool","tool":"<name>","args":{...}} or {"kind":"final","final":"<answer>"}. '
    f"Allowed tools: {', '.join(sorted(ALLOWED_TOOLS))}. "
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
)
