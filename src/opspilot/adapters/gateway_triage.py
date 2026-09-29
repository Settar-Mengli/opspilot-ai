"""Gateway-backed triage adapter (free providers + rules fallback)."""

from __future__ import annotations

import logging

from opspilot.adapters.base import TriageAdapter
from opspilot.adapters.rule_based import RuleBasedAdapter
from opspilot.llm.errors import LlmSchemaError
from opspilot.llm.gateway import LlmGateway
from opspilot.llm.policy import llm_allowed
from opspilot.llm.providers.base import LlmProvider
from opspilot.llm.routing import build_providers
from opspilot.llm.schemas.triage import TriagePayload
from opspilot.llm.types import Message
from opspilot.models.schemas import TriageRecord, WorkItem

logger = logging.getLogger("opspilot.adapters.gateway_triage")

_SYSTEM = (
    "You are an operations triage assistant. Classify the work item. "
    "Respond with JSON only matching the schema. No markdown."
)
_BODY_MAX = 800
_SUBJECT_MAX = 160


class GatewayTriageAdapter(TriageAdapter):
    """Triage via LLM gateway; fail closed to rules."""

    def __init__(self) -> None:
        self._fallback = RuleBasedAdapter()

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
        user = (
            f"<item id={item.id!s}>\n"
            f"source={item.source_type[:32]}\n"
            f"subject={item.subject_or_title[:_SUBJECT_MAX]}\n"
            f"body={item.body_or_description[:_BODY_MAX]}\n"
            f"sender={item.sender_or_requester[:80]}\n"
            f"tags={','.join(item.tags)[:120]}\n"
            f"</item>"
        )
        gw = LlmGateway(providers, observe=True)
        try:
            payload = gw.complete_json(
                task="triage",
                messages=[Message(role="system", content=_SYSTEM), Message(role="user", content=user)],
                schema=TriagePayload,
                max_tokens=300,
            )
        except LlmSchemaError as exc:
            raise ValueError(str(exc)) from exc
        return TriageRecord(
            id=item.id,
            urgency=payload.urgency,
            urgency_reason=payload.urgency_reason,
            category=payload.category,
            category_reason=payload.category_reason,
            sentiment=payload.sentiment,
            sentiment_reason=payload.sentiment_reason,
        )
