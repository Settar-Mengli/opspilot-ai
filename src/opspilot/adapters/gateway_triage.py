"""Gateway-backed triage adapter (free providers + rules fallback)."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from opspilot.adapters.base import TriageAdapter
from opspilot.adapters.rule_based import RuleBasedAdapter
from opspilot.llm.grounding import GroundingError, assert_grounded
from opspilot.llm.policy import llm_allowed
from opspilot.llm.prompt_safety import UNTRUSTED_SYSTEM_POLICY, neutralize_text, wrap_untrusted
from opspilot.llm.providers.base import LlmProvider
from opspilot.llm.routing import build_providers
from opspilot.llm.schemas.triage import TriagePayload
from opspilot.models.schemas import TriageRecord, WorkItem
from opspilot.services._llm import complete_structured

logger = logging.getLogger("opspilot.adapters.gateway_triage")

_SYSTEM = (
    "You are an operations triage assistant. Classify the work item. "
    f"{UNTRUSTED_SYSTEM_POLICY} "
    "Include confidence (0-1) and evidence_refs citing only the item id. "
    "Respond with JSON only matching the schema. No markdown."
)
_BODY_MAX = 500
_SUBJECT_MAX = 160
# Shared with live evals: Groq strict decode needs headroom for P12 fields.
_STRUCTURED_MAX_TOKENS = 1024


def build_triage_user_prompt(item: WorkItem) -> str:
    """Build delimiter-wrapped triage user prompt (P8 / P11)."""
    inner = (
        f"source={neutralize_text(item.source_type)[:32]}\n"
        f"subject={neutralize_text(item.subject_or_title)[:_SUBJECT_MAX]}\n"
        f"body={neutralize_text(item.body_or_description)[:_BODY_MAX]}\n"
        f"sender={neutralize_text(item.sender_or_requester)[:80]}\n"
        f"tags={neutralize_text(','.join(item.tags))[:120]}"
    )
    return wrap_untrusted(item.id, inner)


class GatewayTriageAdapter(TriageAdapter):
    """Triage via LLM gateway; fail closed to rules."""

    def __init__(self, *, session: Session | None = None) -> None:
        self._fallback = RuleBasedAdapter()
        self._session = session

    def classify(self, item: WorkItem) -> TriageRecord:
        if not llm_allowed():
            return self._fallback.classify(item)
        providers = build_providers()
        if not providers:
            return self._fallback.classify(item)
        try:
            return self._classify_gateway(item, providers)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Gateway triage failed for %s, using rules: %s", item.id, exc)
            return self._fallback.classify(item)

    def _classify_gateway(self, item: WorkItem, providers: list[LlmProvider]) -> TriageRecord:
        user = build_triage_user_prompt(item)
        payload = complete_structured(
            task="triage",
            system=_SYSTEM,
            user=user,
            schema=TriagePayload,
            max_tokens=_STRUCTURED_MAX_TOKENS,
            session=self._session,
        )
        if payload is None:
            return self._fallback.classify(item)
        try:
            assert_grounded(payload, allowed_ids={item.id})
        except GroundingError as exc:
            logger.warning("Gateway triage grounding failed for %s: %s", item.id, exc)
            return self._fallback.classify(item)
        return TriageRecord(
            id=item.id,
            urgency=payload.urgency,
            urgency_reason=payload.urgency_reason,
            category=payload.category,
            category_reason=payload.category_reason,
            sentiment=payload.sentiment,
            sentiment_reason=payload.sentiment_reason,
            confidence=payload.confidence,
            evidence_refs=list(payload.evidence_refs),
        )
