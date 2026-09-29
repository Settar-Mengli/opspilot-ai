"""Central remote-LLM allow policy (FORCE_RULES / LLM_DISABLE)."""

from __future__ import annotations

import os

_TRUTHY = frozenset({"1", "true", "yes", "on"})


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in _TRUTHY


def force_rules_enabled() -> bool:
    """Return True when OPSPILOT_FORCE_RULES requests no remote LLM."""
    return _env_truthy("OPSPILOT_FORCE_RULES")


def llm_disable_enabled() -> bool:
    """Return True when OPSPILOT_LLM_DISABLE requests no remote LLM."""
    return _env_truthy("OPSPILOT_LLM_DISABLE")


def llm_allowed() -> bool:
    """Return True when remote LLM calls are permitted.

    When False, every call site must use rules / soft / template fallbacks
    and must not construct provider clients.
    """
    if force_rules_enabled():
        return False
    if llm_disable_enabled():
        return False
    return True
