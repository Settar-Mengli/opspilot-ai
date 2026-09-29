"""Ask service — free-form Q&A via LLM gateway."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from opspilot.services._llm import compact_triage_lines, complete_prose

_SOFT_UNAVAILABLE = "I ran into an issue answering that. The API may be unavailable. Please try again in a moment."
_SOFT_NO_PROVIDER = (
    "I need a free-tier LLM key to answer questions. "
    "Set GEMINI_API_KEY or GROQ_API_KEY (see .env.example) and I'll be ready."
)


def answer_question(
    question: str,
    assistant_name: str = "OpsPilot",
    triage_records: list[dict[str, Any]] | None = None,
    *,
    session: Session | None = None,
) -> str:
    if not question or not question.strip():
        return "I didn't catch a question. What would you like to know?"

    records = triage_records or []
    system = (
        f"You are {assistant_name}, OpsPilot chief of staff. Calm, concise, first person. "
        f"Cite item IDs when useful. Under 200 words. No markdown headers.\n"
        f"Context:\n{compact_triage_lines(records)}"
    )
    result = complete_prose(
        task="ask",
        system=system,
        user=question.strip(),
        max_tokens=800,
        session=session,
    )
    if result is None:
        from opspilot.llm.policy import llm_allowed
        from opspilot.services._llm import providers_or_empty

        if not llm_allowed():
            return _SOFT_UNAVAILABLE
        if not providers_or_empty():
            return _SOFT_NO_PROVIDER
        return _SOFT_UNAVAILABLE
    return result.text.strip() or _SOFT_UNAVAILABLE
