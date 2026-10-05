"""Request-scoped operator authorization for Anthropic (D-023 b6.1 TARGET)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OperatorAnthropicAuth:
    """Capability token: only mint via from_session after verify_session."""

    role: str

    @classmethod
    def from_session(cls, session: Any | None) -> OperatorAnthropicAuth | None:
        """Return auth only for a verified demo_operator session; else None."""
        if session is None:
            return None
        role = getattr(session, "role", None)
        if role != "demo_operator":
            return None
        return cls(role=str(role))
