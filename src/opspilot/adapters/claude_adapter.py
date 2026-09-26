"""Claude-powered triage adapter using the Anthropic API."""

import json
import logging
import os

import anthropic

from opspilot.adapters.base import TriageAdapter
from opspilot.adapters.rule_based import RuleBasedAdapter
from opspilot.models.schemas import TriageRecord, WorkItem

logger = logging.getLogger("opspilot.adapters.claude")

SYSTEM_PROMPT = """\
You are an operations triage assistant. Given a work item, \
you must classify it and respond with ONLY a valid JSON object.
No explanation. No markdown. No code fences. Raw JSON only.

The JSON must have exactly these fields:
{
  "urgency": one of "critical", "high", "medium", "low",
  "urgency_reason": one sentence explaining why,
  "category": one of "incident", "request", "admin", "follow_up", "other",
  "category_reason": one sentence explaining why,
  "sentiment": one of "negative", "neutral", "positive",
  "sentiment_reason": one sentence explaining why
}

Base your classification on genuine understanding of the \
content, not keyword matching. Consider context, tone, \
business impact, and urgency signals holistically."""

VALID_URGENCY = {"critical", "high", "medium", "low"}
VALID_CATEGORY = {"incident", "request", "admin", "follow_up", "other"}
VALID_SENTIMENT = {"negative", "neutral", "positive"}


class ClaudeAdapter(TriageAdapter):
    """Triage adapter that uses Claude for classification with rule-based fallback."""

    def __init__(self) -> None:
        self._api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not self._api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set.")
        self._client = anthropic.Anthropic(api_key=self._api_key)
        self._fallback = RuleBasedAdapter()

    def classify(self, item: WorkItem) -> TriageRecord:
        try:
            return self._classify_with_claude(item)
        except Exception as exc:
            logger.warning(
                "Claude classification failed for %s, falling back to rules: %s",
                item.id,
                exc,
            )
            return self._fallback.classify(item)

    def _classify_with_claude(self, item: WorkItem) -> TriageRecord:
        user_message = (
            f"Work Item ID: {item.id}\n"
            f"Source Type: {item.source_type}\n"
            f"Subject: {item.subject_or_title}\n"
            f"Body: {item.body_or_description}\n"
            f"Sender: {item.sender_or_requester}\n"
            f"Tags: {', '.join(item.tags)}"
        )

        response = self._client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            temperature=0.1,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        raw_text = response.content[0].text
        # Strip markdown code fences if present
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            # Remove opening fence (with optional language tag)
            first_newline = cleaned.index("\n")
            cleaned = cleaned[first_newline + 1:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
        parsed = json.loads(cleaned)

        # Validate required fields and values
        urgency = parsed["urgency"]
        category = parsed["category"]
        sentiment = parsed["sentiment"]

        if urgency not in VALID_URGENCY:
            raise ValueError(f"Invalid urgency value: {urgency}")
        if category not in VALID_CATEGORY:
            raise ValueError(f"Invalid category value: {category}")
        if sentiment not in VALID_SENTIMENT:
            raise ValueError(f"Invalid sentiment value: {sentiment}")

        return TriageRecord(
            id=item.id,
            urgency=urgency,
            urgency_reason=str(parsed["urgency_reason"]),
            category=category,
            category_reason=str(parsed["category_reason"]),
            sentiment=sentiment,
            sentiment_reason=str(parsed["sentiment_reason"]),
        )
