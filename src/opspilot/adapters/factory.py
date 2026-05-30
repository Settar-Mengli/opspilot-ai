"""Factory for selecting the appropriate triage adapter at runtime."""

import logging

from opspilot.adapters.base import TriageAdapter
from opspilot.adapters.rule_based import RuleBasedAdapter


logger = logging.getLogger("opspilot.adapters.factory")


def get_adapter() -> TriageAdapter:
    """Return the best available triage adapter.

    Tries Claude first; falls back to rule-based if the API key
    is missing or the SDK is unavailable.
    """
    try:
        from opspilot.adapters.claude_adapter import ClaudeAdapter

        return ClaudeAdapter()
    except (ValueError, ImportError) as exc:
        logger.info("Claude adapter unavailable, using rule-based fallback: %s", exc)
        return RuleBasedAdapter()
