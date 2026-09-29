"""Insights service — structured cross-cutting analysis via gateway."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from opspilot.llm.policy import llm_allowed
from opspilot.llm.schemas.insights import InsightsPayload
from opspilot.services._llm import compact_triage_lines, complete_structured, providers_or_empty

logger = logging.getLogger(__name__)

_SOFT = "I ran into an issue analyzing the data. The API may be unavailable. Please try again in a moment."
_SOFT_NO_PROVIDER = (
    "I'd love to share patterns from your data, but I need a free-tier LLM key first. "
    "Set GEMINI_API_KEY or GROQ_API_KEY (see .env.example) and I'll be ready."
)


def _fallback(reason: str) -> dict[str, Any]:
    return {"intro": reason, "insights": []}


def generate_insights(
    assistant_name: str = "OpsPilot",
    triage_records: list[dict[str, Any]] | None = None,
    *,
    session: Session | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    if not llm_allowed():
        return _fallback(_SOFT)
    if not providers_or_empty():
        return _fallback(_SOFT_NO_PROVIDER)

    records = triage_records or []
    # Empty queue: soft path (empty insights list is valid only when there is nothing to analyze).
    # Non-empty queue: InsightsPayload requires min_length=1 insights; empty list → repair/failover/soft.
    if not records:
        return _fallback("The queue is empty — nothing to analyze yet.")

    system = (
        f"You are {assistant_name}, OpsPilot chief of staff. Find cross-cutting patterns "
        "(not per-item summaries). Return JSON only matching the schema. 1-5 insights."
    )
    user = compact_triage_lines(records, include_title=True)
    payload = complete_structured(
        task="insights",
        system=system,
        user=user,
        schema=InsightsPayload,
        max_tokens=2048,
        session=session,
        request_id=request_id,
    )
    if payload is None:
        return _fallback(_SOFT)

    return {
        "intro": payload.intro,
        "insights": [{"title": i.title, "body": i.body, "category": i.category or "general"} for i in payload.insights],
    }
