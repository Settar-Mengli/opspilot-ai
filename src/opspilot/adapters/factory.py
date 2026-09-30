"""Factory for selecting the appropriate triage adapter at runtime."""

import logging

from sqlalchemy.orm import Session

from opspilot.adapters.base import TriageAdapter
from opspilot.adapters.rule_based import RuleBasedAdapter
from opspilot.llm.policy import force_rules_enabled, llm_allowed
from opspilot.llm.routing import build_providers

logger = logging.getLogger("opspilot.adapters.factory")


def get_adapter(*, session: Session | None = None) -> TriageAdapter:
    """Return the best available triage adapter.

    When remote LLM is disallowed (OPSPILOT_FORCE_RULES / OPSPILOT_LLM_DISABLE),
    always returns RuleBasedAdapter. Otherwise uses free-provider gateway triage
    when keys are configured; else rule-based. Session is required for budget debit.
    """
    if not llm_allowed():
        if force_rules_enabled():
            logger.warning("OPSPILOT_FORCE_RULES set; using rule-based adapter (tests/CI only — do not set in deploy)")
        else:
            logger.warning("OPSPILOT_LLM_DISABLE set; using rule-based adapter")
        return RuleBasedAdapter()

    if build_providers():
        from opspilot.adapters.gateway_triage import GatewayTriageAdapter

        logger.info("Using gateway triage adapter")
        return GatewayTriageAdapter(session=session)

    logger.info("No free-tier LLM keys configured; using rule-based triage")
    return RuleBasedAdapter()
