"""Insights adapter — generates structured cross-cutting observations.

Takes the current triage records and asks Claude to identify patterns,
themes, and observations a chief of staff would notice — not just a
restatement of items but actual cross-cutting analysis.

Returns a structured dict with an intro paragraph and a list of insights.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from anthropic import Anthropic

logger = logging.getLogger(__name__)

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 1200


def _build_system_prompt(assistant_name: str) -> str:
    return f"""You are {assistant_name}, an AI chief of staff inside the OpsPilot platform. The user wants cross-cutting insights — patterns, themes, and observations across their operational items.

Your job is NOT to summarize individual items. Your job is to NOTICE THINGS:
- Clusters of items in the same category that might be related
- Patterns that suggest deeper organizational issues (e.g. "3 escalations from finance this week — process gap?")
- Items that have been open longer than expected
- Items where ownership or accountability seems unclear
- Themes across urgency levels (e.g. "All your customer items are escalations — none proactive")
- Anything a good chief of staff would lean over and say "I've been noticing..."

Voice and tone:
- Specific. Reference item IDs (e.g. WI-001) when relevant.
- Warm but direct. Like a trusted advisor flagging something useful.
- Not alarmist. Not flattering. Just observant.
- Each insight should make the user think "Oh, that's interesting" — not "Yeah, I know that."

Output format:
You MUST respond with ONLY valid JSON, no markdown code fences, no preamble. The exact shape:

{{
  "intro": "A single short paragraph (2-3 sentences) opening the analysis. Sets the tone for the day's patterns.",
  "insights": [
    {{
      "title": "A short title (under 60 chars) — the headline insight.",
      "body": "2-3 sentences expanding the insight. Reference specific item IDs if relevant. Suggest one concrete next step if appropriate.",
      "category": "category-tag-string-lowercase"
    }}
  ]
}}

Constraints:
- Return between 3 and 5 insights (no more, no less)
- The "category" field is a single lowercase tag like "ownership", "pattern", "risk", "process", "tempo", "people", "finance", etc. Pick the most fitting one.
- Total response under 800 words
- If the triage queue is empty or has only 1-2 items, return fewer insights (1-2) and acknowledge the quiet state in the intro
- If you cannot find meaningful patterns, return a single honest insight saying so — do NOT invent patterns"""


def _format_records_for_analysis(records: list[dict[str, Any]]) -> str:
    if not records:
        return "The triage queue is empty."
    lines = ["Triage queue for analysis:"]
    for record in records:
        item_id = record.get("id", "?")
        urgency = record.get("urgency", "unknown")
        category = record.get("category", "uncategorized")
        reason = record.get("urgency_reason", "")
        title = record.get("subject_or_title", "")
        lines.append(f"- {item_id} | {urgency} | {category} | {title}: {reason}")
    return "\n".join(lines)


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences if Claude wrapped the JSON in them."""
    text = text.strip()
    # Match ```json ... ``` or ``` ... ```
    pattern = r"^```(?:json)?\s*\n?(.*?)\n?```$"
    match = re.match(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


def _fallback_response(reason: str) -> dict[str, Any]:
    """Return a graceful fallback when analysis cannot be performed."""
    return {
        "intro": reason,
        "insights": [],
    }


def generate_insights(
    assistant_name: str = "OpsPilot",
    triage_records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Generate structured cross-cutting insights from triage data.

    Returns a dict with keys "intro" (string) and "insights" (list of dicts
    each with "title", "body", "category"). Falls back gracefully on errors.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return _fallback_response(
            "I'd love to share patterns from your data, but I need an Anthropic API key first. "
            "Set ANTHROPIC_API_KEY in your environment and I'll be ready."
        )

    records = triage_records or []
    system_prompt = _build_system_prompt(assistant_name)
    user_message = _format_records_for_analysis(records)

    try:
        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        if not response.content or len(response.content) == 0:
            return _fallback_response("I wasn't able to analyze the data this time. Please try again.")

        text_block = response.content[0]
        if not hasattr(text_block, "text"):
            return _fallback_response("I received an unexpected response shape. Please try again.")

        raw_text = text_block.text.strip()
        cleaned = _strip_code_fences(raw_text)

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.warning("Insights JSON parse failed: %s. Raw text: %s", exc, raw_text[:300])
            return _fallback_response("I had trouble structuring my analysis. Please try refreshing.")

        # Validate the shape
        if not isinstance(parsed, dict):
            return _fallback_response("Analysis returned an unexpected shape.")
        intro = parsed.get("intro", "")
        insights = parsed.get("insights", [])
        if not isinstance(intro, str):
            intro = ""
        if not isinstance(insights, list):
            insights = []

        # Sanitize each insight
        clean_insights = []
        for item in insights:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "")).strip()
            body = str(item.get("body", "")).strip()
            category = str(item.get("category", "")).strip().lower()
            if title and body:
                clean_insights.append(
                    {
                        "title": title,
                        "body": body,
                        "category": category or "general",
                    }
                )

        return {
            "intro": intro,
            "insights": clean_insights,
        }
    except Exception as exc:
        logger.exception("Insights adapter error: %s", exc)
        return _fallback_response(
            "I ran into an issue analyzing the data. The API may be unavailable. Please try again in a moment."
        )
