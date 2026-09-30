"""Per-provider circuit breaker (default 5 minutes open)."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field


def _open_seconds() -> float:
    raw = os.environ.get("OPSPILOT_LLM_CIRCUIT_OPEN_SECONDS", "300").strip()
    try:
        return max(1.0, float(raw))
    except ValueError:
        return 300.0


@dataclass
class CircuitBreaker:
    """Simple open/closed circuit keyed by provider name."""

    open_seconds: float = field(default_factory=_open_seconds)
    _opened_until: dict[str, float] = field(default_factory=dict)

    def is_open(self, provider: str) -> bool:
        until = self._opened_until.get(provider, 0.0)
        if until <= 0:
            return False
        if time.monotonic() >= until:
            self._opened_until.pop(provider, None)
            return False
        return True

    def trip(self, provider: str) -> None:
        self._opened_until[provider] = time.monotonic() + self.open_seconds

    def reset(self, provider: str) -> None:
        self._opened_until.pop(provider, None)
