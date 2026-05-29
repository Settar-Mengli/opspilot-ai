from collections import Counter

from opspilot.models.schemas import ActionItem, TriageRecord, WorkItem


def generate_daily_briefing(
    run_date: str,
    triage_records: list[TriageRecord],
    action_items: list[ActionItem],
    work_items: list[WorkItem],
) -> str:
    total = len(triage_records)
    urgency_counts = Counter(record.urgency for record in triage_records)
    sentiment_counts = Counter(record.sentiment for record in triage_records)
    titles_by_id = {item.id: item.subject_or_title for item in work_items}

    high_priority = [record.id for record in triage_records if record.urgency in {"critical", "high"}]
    due_soon = [action for action in action_items if action.deadline in {"EOD", "tomorrow"}]

    lines = [
        f"OpsPilot AI Daily Executive Briefing - {run_date}",
        "",
        f"Total Work Items: {total}",
        f"Urgency Mix: critical={urgency_counts.get('critical', 0)}, high={urgency_counts.get('high', 0)}, medium={urgency_counts.get('medium', 0)}, low={urgency_counts.get('low', 0)}",
        f"Sentiment Mix: negative={sentiment_counts.get('negative', 0)}, neutral={sentiment_counts.get('neutral', 0)}, positive={sentiment_counts.get('positive', 0)}",
        "",
        "Top Priorities:",
    ]

    if high_priority:
        for work_item_id in high_priority[:5]:
            title = titles_by_id.get(work_item_id, "(title unavailable)")
            lines.append(f"- {work_item_id}: {title}")
    else:
        lines.append("- None")

    lines.append("")
    lines.append("Due-Soon Action Items:")
    if due_soon:
        for action in due_soon[:5]:
            owner = action.owner or "unassigned"
            lines.append(f"- {action.work_item_id}: {action.summary} (owner={owner}, deadline={action.deadline})")
    else:
        lines.append("- None")

    return "\n".join(lines) + "\n"
