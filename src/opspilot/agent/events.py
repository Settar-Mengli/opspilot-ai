"""SSE / agent event payloads (D-032)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

EventType = Literal["token", "tool_start", "tool_end", "draft", "final", "error"]


@dataclass(frozen=True)
class AgentEvent:
    type: EventType
    request_id: str
    data: dict[str, Any] = field(default_factory=dict)


def event_dict(event: AgentEvent) -> dict[str, Any]:
    payload = asdict(event)
    # Flatten for SSE JSON: type, request_id, + data keys
    out: dict[str, Any] = {"type": payload["type"], "request_id": payload["request_id"]}
    out.update(payload.get("data") or {})
    return out
