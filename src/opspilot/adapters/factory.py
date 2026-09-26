"""Factory for selecting the appropriate triage adapter at runtime."""

import logging
import os

from opspilot.adapters.base import TriageAdapter
from opspilot.adapters.rule_based import RuleBasedAdapter

logger = logging.getLogger("opspilot.adapters.factory")

_FORCE_RULES_TRUTHY = frozenset({"1", "true", "yes", "on"})


def _force_rules_enabled() -> bool:
    """Return True when OPSPILOT_FORCE_RULES requests rule-based triage only.

    Default is off (unset/empty/false). Documented in .env.example.
    Tests and hermetic CI set this so the Anthropic client is never constructed.
    Subprocesses inherit the env var from the parent process.
    """
    return os.environ.get("OPSPILOT_FORCE_RULES", "").strip().lower() in _FORCE_RULES_TRUTHY


def get_adapter() -> TriageAdapter:
    """Return the best available triage adapter.

    When OPSPILOT_FORCE_RULES is truthy, always returns RuleBasedAdapter.
    Otherwise tries Claude first; falls back to rule-based if the API key
    is missing or the SDK is unavailable.
    """
    if _force_rules_enabled():
        logger.info("OPSPILOT_FORCE_RULES set; using rule-based adapter")
        return RuleBasedAdapter()

    try:
        from opspilot.adapters.claude_adapter import ClaudeAdapter

        return ClaudeAdapter()
    except (ValueError, ImportError) as exc:
        logger.info("Claude adapter unavailable, using rule-based fallback: %s", exc)
        return RuleBasedAdapter()
