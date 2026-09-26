"""AI-generated executive briefing using Claude."""

import logging
import os

logger = logging.getLogger("opspilot.adapters.briefing")

URGENCY_ORDER = ["critical", "high", "medium", "low"]


def generate_ai_briefing(
    run_date: str,
    triage_records: list,
    action_items: list,
    normalized_items: list,
    fallback_briefing: str,
) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return fallback_briefing

    try:
        import anthropic

        # Build urgency counts
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

        # Top 3 items by urgency
        def urgency_rank(rec):
            urg = rec.get("urgency", "low") if isinstance(rec, dict) else getattr(rec, "urgency", "low")
            return URGENCY_ORDER.index(urg) if urg in URGENCY_ORDER else 99

        sorted_records = sorted(
            zip(triage_records, normalized_items, strict=False),
            key=lambda pair: urgency_rank(pair[0]),
        )
        top_3_lines = []
        for record, item in sorted_records[:3]:
            rec_id = record.get("id", "") if isinstance(record, dict) else getattr(record, "id", "")
            urg = record.get("urgency", "") if isinstance(record, dict) else getattr(record, "urgency", "")
            cat = record.get("category", "") if isinstance(record, dict) else getattr(record, "category", "")
            if isinstance(item, dict):
                subject = item.get("subject_or_title") or ""
            else:
                subject = getattr(item, "subject_or_title", None) or ""
            top_3_lines.append(f"- {rec_id}: {subject} (urgency={urg}, category={cat})")

        # Action items with deadlines
        deadline_lines = []
        for action in action_items:
            deadline = action.get("deadline", None) if isinstance(action, dict) else getattr(action, "deadline", None)
            if deadline:
                aid = (
                    action.get("work_item_id", "") if isinstance(action, dict) else getattr(action, "work_item_id", "")
                )
                summary = action.get("summary", "") if isinstance(action, dict) else getattr(action, "summary", "")
                owner = (
                    action.get("owner", "unassigned")
                    if isinstance(action, dict)
                    else getattr(action, "owner", "unassigned")
                )
                deadline_lines.append(f"- {aid}: {summary} (owner: {owner}, deadline: {deadline})")

        formatted_top = "\n".join(top_3_lines) if top_3_lines else "None"
        formatted_deadlines = "\n".join(deadline_lines) if deadline_lines else "None today"

        system_prompt = (
            "You are a chief of staff writing a daily executive briefing "
            "for an operations leader. Write in clear, confident prose. "
            "No bullet points in the opening paragraph. Be specific about "
            "what needs attention today and why. Sound like a senior human "
            "analyst, not a template. Maximum 250 words."
        )

        user_message = (
            f"Date: {run_date}\n\n"
            f"Triage Summary:\n"
            f"- Total items: {len(triage_records)}\n"
            f"- Critical: {urgency_counts['critical']}, High: {urgency_counts['high']}, "
            f"Medium: {urgency_counts['medium']}, Low: {urgency_counts['low']}\n"
            f"- Negative sentiment signals: {sentiment_counts['negative']}\n\n"
            f"Top Priority Items:\n{formatted_top}\n\n"
            f"Items with Deadlines:\n{formatted_deadlines}\n\n"
            f"Write a daily executive briefing based on this data."
        )

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=800,
            temperature=0.3,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        return response.content[0].text

    except Exception as exc:
        logger.warning("AI briefing generation failed, using fallback: %s", exc)
        return fallback_briefing
