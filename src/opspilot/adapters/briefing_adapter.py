"""AI-generated executive briefing via LLM gateway."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from opspilot.llm.policy import llm_allowed
from opspilot.llm.prompt_safety import UNTRUSTED_SYSTEM_POLICY, neutralize_text, wrap_untrusted
from opspilot.services._llm import complete_prose, format_work_item_id_for_prompt, providers_or_empty

logger = logging.getLogger("opspilot.adapters.briefing")

URGENCY_ORDER = ["critical", "high", "medium", "low"]


def generate_ai_briefing(
    run_date: str,
    triage_records: list[Any],
    action_items: list[Any],
    normalized_items: list[Any],
    fallback_briefing: str,
    *,
    session: Session | None = None,
) -> str:
    if not llm_allowed() or not providers_or_empty():
        return fallback_briefing

    try:
        urgency_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        sentiment_counts = {"negative": 0, "neutral": 0, "positive": 0}

        for record in triage_records:
            urg = (
                getattr(record, "urgency", None) or record.get("urgency", "low")
                if isinstance(record, dict)
                else record.urgency
            )
            sent = (
                getattr(record, "sentiment", None) or record.get("sentiment", "neutral")
                if isinstance(record, dict)
                else record.sentiment
            )
            urgency_counts[urg] = urgency_counts.get(urg, 0) + 1
            sentiment_counts[sent] = sentiment_counts.get(sent, 0) + 1

        def urgency_rank(rec: Any) -> int:
            urg = rec.get("urgency", "low") if isinstance(rec, dict) else getattr(rec, "urgency", "low")
            return URGENCY_ORDER.index(urg) if urg in URGENCY_ORDER else 99

        sorted_records = sorted(
            zip(triage_records, normalized_items, strict=False),
            key=lambda pair: urgency_rank(pair[0]),
        )
        top_3_lines = []
        for record, item in sorted_records[:3]:
            rec_id = format_work_item_id_for_prompt(
                record.get("id", "") if isinstance(record, dict) else getattr(record, "id", "")
            )
            urg = record.get("urgency", "") if isinstance(record, dict) else getattr(record, "urgency", "")
            cat = record.get("category", "") if isinstance(record, dict) else getattr(record, "category", "")
            if isinstance(item, dict):
                subject = neutralize_text(str(item.get("subject_or_title") or ""))[:80]
            else:
                subject = neutralize_text(str(getattr(item, "subject_or_title", None) or ""))[:80]
            top_3_lines.append(f"- {rec_id}: {subject} (urgency={urg}, category={cat})")

        deadline_lines = []
        for action in action_items[:10]:
            deadline = action.get("deadline", None) if isinstance(action, dict) else getattr(action, "deadline", None)
            if deadline:
                aid = format_work_item_id_for_prompt(
                    action.get("work_item_id", "") if isinstance(action, dict) else getattr(action, "work_item_id", "")
                )
                summary = neutralize_text(
                    str(action.get("summary", "") if isinstance(action, dict) else getattr(action, "summary", ""))
                )[:100]
                owner = (
                    action.get("owner", "unassigned")
                    if isinstance(action, dict)
                    else getattr(action, "owner", "unassigned")
                )
                deadline_lines.append(f"- {aid}: {summary} (owner: {owner}, deadline: {deadline})")

        formatted_top = "\n".join(top_3_lines) if top_3_lines else "None"
        formatted_deadlines = "\n".join(deadline_lines) if deadline_lines else "None today"
        untrusted_blob = wrap_untrusted(
            "briefing",
            f"Top:\n{formatted_top}\nDeadlines:\n{formatted_deadlines}",
        )

        system = (
            "You are a chief of staff writing a daily executive briefing. "
            f"Clear confident prose. Max 250 words. No bullet-only opening. {UNTRUSTED_SYSTEM_POLICY}"
        )
        user = (
            f"Date: {run_date}\n"
            f"Total: {len(triage_records)} "
            f"C/H/M/L={urgency_counts['critical']}/{urgency_counts['high']}/"
            f"{urgency_counts['medium']}/{urgency_counts['low']} "
            f"neg={sentiment_counts['negative']}\n"
            f"{untrusted_blob}\n"
            "Write the briefing."
        )
        result = complete_prose(task="briefing", system=system, user=user, max_tokens=800, session=session)
        if result is None or not result.text.strip():
            return fallback_briefing
        return result.text.strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("AI briefing generation failed, using fallback: %s", exc)
        return fallback_briefing
