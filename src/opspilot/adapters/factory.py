"""Factory for selecting the appropriate triage adapter at runtime."""

import logging

from opspilot.adapters.base import TriageAdapter
from opspilot.adapters.rule_based import RuleBasedAdapter
from opspilot.llm.policy import force_rules_enabled, llm_allowed

logger = logging.getLogger("opspilot.adapters.factory")


def get_adapter() -> TriageAdapter:
    """Return the best available triage adapter.

    When remote LLM is disallowed (OPSPILOT_FORCE_RULES / OPSPILOT_LLM_DISABLE),
    always returns RuleBasedAdapter. Otherwise tries Claude first; falls back
    to rule-based if the API key is missing or the SDK is unavailable.
    """
    if not llm_allowed():
        if force_rules_enabled():
            logger.warning("OPSPILOT_FORCE_RULES set; using rule-based adapter (tests/CI only — do not set in deploy)")
        else:
            logger.warning("OPSPILOT_LLM_DISABLE set; using rule-based adapter")
        return RuleBasedAdapter()

    try:
        from opspilot.adapters.claude_adapter import ClaudeAdapter

        return ClaudeAdapter()
    except (ValueError, ImportError) as exc:
        logger.info("Claude adapter unavailable, using rule-based fallback: %s", exc)
        return RuleBasedAdapter()
