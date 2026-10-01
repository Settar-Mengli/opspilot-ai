"""JSON-emulated agent turn schema + parse helpers (D-031)."""

from __future__ import annotations

from typing import Any, Literal, Self

from pydantic import BaseModel, Field, field_validator, model_validator

ALLOWED_TOOLS = frozenset({"search_items", "get_message", "get_calendar", "draft_reply"})


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
    "Never invent a send tool. Cite item IDs when useful. Under 200 words for final."
)
