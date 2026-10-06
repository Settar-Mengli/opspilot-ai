"""Request-scoped operator authorization for Anthropic (D-023 b6.1 TARGET)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from opspilot.services.operator_session import OperatorSession


@dataclass(frozen=True)
class OperatorAnthropicAuth:
    """Capability token: only mint via from_session after verify_session."""

    role: str

    @classmethod
    def from_session(cls, session: OperatorSession | None) -> OperatorAnthropicAuth | None:
        """Return auth only for a real OperatorSession with demo_operator role; else None."""
        from opspilot.services.operator_session import OperatorSession as _OperatorSession

        if session is None:
            return None
        if not isinstance(session, _OperatorSession):
            return None
        if session.role != "demo_operator":
            return None
        return OperatorAnthropicAuth(role=session.role)
