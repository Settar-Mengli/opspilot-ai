"""Evening summary service via LLM gateway."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from opspilot.llm.policy import llm_allowed
from opspilot.services._llm import compact_triage_lines, complete_prose, providers_or_empty

_SOFT_UNAVAILABLE = (
    "I ran into an issue preparing your end-of-day summary. The API may be unavailable. Please try again in a moment."
)
_SOFT_NO_PROVIDER = (
    "I'd love to wrap up your day for you, but I need a free-tier LLM key first. "
    "Set GEMINI_API_KEY or GROQ_API_KEY (see .env.example) and I'll be ready."
)


def generate_evening_summary(
    assistant_name: str = "OpsPilot",
    triage_records: list[dict[str, Any]] | None = None,
    *,
    session: Session | None = None,
) -> str:
    records = triage_records or []
    system = (
        f"You are {assistant_name}, OpsPilot chief of staff delivering an end-of-day summary. "
        "Calm, warm, first person. Under 200 words, three short paragraphs max. Prose only. "
        "Cover: lead story, what is still open, what to carry into tomorrow."
    )
    user = compact_triage_lines(records)
    result = complete_prose(task="evening", system=system, user=user, max_tokens=700, session=session)
    if result is None:
        if not llm_allowed():
            return _SOFT_UNAVAILABLE
        if not providers_or_empty():
            return _SOFT_NO_PROVIDER
        return _SOFT_UNAVAILABLE
    return result.text.strip() or _SOFT_UNAVAILABLE
