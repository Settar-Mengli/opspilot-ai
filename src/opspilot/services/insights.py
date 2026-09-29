"""Insights service — structured cross-cutting analysis via gateway."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from opspilot.llm.errors import LlmSchemaError
from opspilot.llm.gateway import LlmGateway, session_attempt_recorder
from opspilot.llm.policy import llm_allowed
from opspilot.llm.schemas.insights import InsightsPayload
from opspilot.llm.types import Message
from opspilot.services._llm import compact_triage_lines, providers_or_empty

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
) -> dict[str, Any]:
    if not llm_allowed():
        return _fallback(_SOFT)
    providers = providers_or_empty()
    if not providers:
        return _fallback(_SOFT_NO_PROVIDER)

    records = triage_records or []
    system = (
        f"You are {assistant_name}, OpsPilot chief of staff. Find cross-cutting patterns "
        "(not per-item summaries). Return JSON only matching the schema. 1-5 insights."
    )
    user = compact_triage_lines(records, include_title=True)
    recorder = session_attempt_recorder(session) if session is not None else None
    # complete_json uses LlmGateway (repair once); budget debit is best-effort via first provider only in B2.
    gw = LlmGateway(providers, recorder=recorder, observe=True)
    try:
        payload = gw.complete_json(
            task="insights",
            messages=[Message(role="system", content=system), Message(role="user", content=user)],
            schema=InsightsPayload,
            max_tokens=1200,
        )
    except LlmSchemaError:
        return _fallback("I had trouble structuring my analysis. Please try refreshing.")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Insights service error: %s", exc)
        return _fallback(_SOFT)

    return {
        "intro": payload.intro,
        "insights": [{"title": i.title, "body": i.body, "category": i.category or "general"} for i in payload.insights],
    }
