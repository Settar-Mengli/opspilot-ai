"""Evening summary adapter — generates a closing-of-day summary.

Takes the current triage records and asks Claude to summarize what
got attention today, what is still open, and what is worth carrying
into tomorrow. Written in the voice of a chief of staff doing an
end-of-day recap.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from anthropic import Anthropic

logger = logging.getLogger(__name__)

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 700


def _build_system_prompt(assistant_name: str) -> str:
    return f"""You are {assistant_name}, an AI chief of staff inside the OpsPilot platform. You are delivering an end-of-day summary to an executive.

Voice and tone:
- Calm, confident, warm. The day is ending. The tone should feel like a trusted advisor wrapping up the day with their principal.
- Speak in first person ("Today I tracked...", "We closed...", "Tomorrow you'll want to revisit...")
- Reference specific item IDs when relevant (e.g. "WI-001 needed leadership input on the SRE incident")
- Be honest about what is still open — do not pretend everything is handled.
- Keep the summary under 200 words. Three short paragraphs maximum.
- Use prose, not bullet points. Warmer that way.
- Do not use markdown headers.

Structure your summary as:
1. A brief lead — what kind of day it was (busy, balanced, quiet) and the top story.
2. What's still open and why it matters.
3. What's worth carrying into tomorrow.

If the triage queue is empty or contains only low-urgency items, acknowledge that the day was quiet — do not invent activity."""


def _format_records_for_summary(records: list[dict[str, Any]]) -> str:
    if not records:
        return "No items were processed today."
    lines = ["Today's triage queue:"]
    for record in records:
        item_id = record.get("id", "?")
        urgency = record.get("urgency", "unknown")
        category = record.get("category", "uncategorized")
        reason = record.get("urgency_reason", "")
        lines.append(f"- {item_id} | {urgency} | {category} | {reason}")
    return "\n".join(lines)


def generate_evening_summary(
    assistant_name: str = "OpsPilot",
    triage_records: list[dict[str, Any]] | None = None,
) -> str:
    """Generate an end-of-day summary from today's triage data.

    Returns natural-language text. Falls back to a polite message if
    no API key is configured or the API call fails.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return (
            "I'd love to wrap up your day for you, but I need an Anthropic API key first. "
            "Set ANTHROPIC_API_KEY in your environment and I'll be ready."
        )

    records = triage_records or []
    system_prompt = _build_system_prompt(assistant_name)
    user_message = _format_records_for_summary(records)

    try:
        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        if response.content and len(response.content) > 0:
            text_block = response.content[0]
            if hasattr(text_block, "text"):
                return text_block.text.strip()
        return "I wasn't able to wrap up the day. Please try again."
    except Exception as exc:
        logger.exception("Evening summary adapter error: %s", exc)
        return (
            "I ran into an issue preparing your end-of-day summary. "
            "The API may be unavailable. Please try again in a moment."
        )
