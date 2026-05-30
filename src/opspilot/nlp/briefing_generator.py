from collections import Counter
from pathlib import Path

from opspilot.history.run_history import find_previous_run_id, read_run_json_artifact
from opspilot.models.schemas import ActionItem, TriageRecord, WorkItem


PRIORITY_ORDER: list[tuple[str, str]] = [
    ("critical", "Critical"),
    ("high", "High"),
    ("medium", "Medium"),
    ("low", "Low"),
]


def generate_daily_briefing(
    run_date: str,
    triage_records: list[TriageRecord],
    action_items: list[ActionItem],
    work_items: list[WorkItem],
    current_run_id: str | None = None,
    runs_root: Path | None = None,
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

    lines.extend(_render_since_last_run_section(current_run_id, runs_root, triage_records))

    return "\n".join(lines) + "\n"


def _render_since_last_run_section(
    current_run_id: str | None,
    runs_root: Path | None,
    current_triage_records: list[TriageRecord],
) -> list[str]:
    section = ["", "---", "", "## Since Last Run"]

    if not current_run_id or runs_root is None:
        section.append("No previous run available for comparison.")
        section.extend(["", "---"])
        return section

    previous_run_id = find_previous_run_id(current_run_id, runs_root)
    if previous_run_id is None:
        section.append("No previous run available for comparison.")
        section.extend(["", "---"])
        return section

    previous_payload = read_run_json_artifact(previous_run_id, "triage_results.json", runs_root)
    if not isinstance(previous_payload, list):
        section.append("No previous run available for comparison.")
        section.extend(["", "---"])
        return section

    previous_counts = _priority_counts_from_payload(previous_payload)
    current_counts = _priority_counts_from_triage(current_triage_records)

    section.append(f"_Compared to {previous_run_id}_")
    section.append("")
    section.append("| Priority | Previous | Current | Change |")
    section.append("|----------|----------|---------|--------|")

    for priority_key, label in PRIORITY_ORDER:
        previous = previous_counts.get(priority_key, 0)
        current = current_counts.get(priority_key, 0)
        section.append(
            f"| {label} | {previous} | {current} | {_format_priority_change(previous, current)} |"
        )

    section.extend(["", "---"])
    return section


def _priority_counts_from_triage(triage_records: list[TriageRecord]) -> dict[str, int]:
    counts = Counter(record.urgency for record in triage_records)
    return {priority: int(counts.get(priority, 0)) for priority, _ in PRIORITY_ORDER}


def _priority_counts_from_payload(payload: list[object]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        urgency = entry.get("urgency")
        if isinstance(urgency, str):
            counts[urgency] += 1

    return {priority: int(counts.get(priority, 0)) for priority, _ in PRIORITY_ORDER}


def _format_priority_change(previous: int, current: int) -> str:
    delta = current - previous
    if delta == 0:
        return "—"
    if delta > 0:
        return f"+{delta} ↑"
    return f"{delta} ↓"
