"""Conversation adapter — answers free-form questions about OpsPilot state.

Receives a user question plus the current triage records as context,
and returns a natural-language answer in the voice of a chief of staff.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from anthropic import Anthropic

logger = logging.getLogger(__name__)

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 800


def _build_system_prompt(assistant_name: str, triage_records: list[dict[str, Any]]) -> str:
    """Compose the system prompt with triage context."""
    if not triage_records:
        records_summary = "No work items are currently in the triage queue."
    else:
        lines = ["The user's current triage queue contains these items:"]
        for record in triage_records:
            item_id = record.get("id", "?")
            urgency = record.get("urgency", "unknown")
            category = record.get("category", "uncategorized")
            reason = record.get("urgency_reason", "")
            lines.append(f"- {item_id} | urgency: {urgency} | category: {category} | reason: {reason}")
        records_summary = "\n".join(lines)

    return f"""You are {assistant_name}, an AI chief of staff inside the OpsPilot platform. You help an executive understand and act on their operational state.

Voice and tone:
- Calm, confident, concise. Like a trusted advisor, not a chatbot.
- Speak in first person ("I'd recommend...", "I see two patterns...")
- Reference specific item IDs when relevant (e.g. "WI-001 is the one to prioritize")
- Never hedge unnecessarily. Be direct.
- Keep answers under 200 words unless the question genuinely requires more.
- Do not use markdown headers or bullet points unless the user asks for a list. Prose is warmer.

Current state you have visibility into:
{records_summary}

If the user asks something you cannot answer from the triage data alone (e.g. specific calendar details, email contents, Slack messages), say so honestly and note that integration is on the roadmap. Do not invent data."""


def answer_question(
    question: str,
    assistant_name: str = "OpsPilot",
    triage_records: list[dict[str, Any]] | None = None,
) -> str:
    """Answer a free-form question with triage context.

    Returns a natural-language answer. Falls back to a polite message
    if no API key is configured or the API call fails.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return (
            "I need an Anthropic API key to answer questions. "
            "Set ANTHROPIC_API_KEY in your environment and I'll be ready."
        )

    if not question or not question.strip():
        return "I didn't catch a question. What would you like to know?"

    records = triage_records or []
    system_prompt = _build_system_prompt(assistant_name, records)

    try:
        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": question.strip()}],
        )
        # Extract text from the response
        if response.content and len(response.content) > 0:
            text_block = response.content[0]
            if hasattr(text_block, "text"):
                return text_block.text.strip()
        return "I wasn't able to generate a response. Please try again."
    except Exception as exc:
        logger.exception("Conversation adapter error: %s", exc)
        return (
            "I ran into an issue answering that. The API may be unavailable. "
            "Please try again in a moment."
        )
