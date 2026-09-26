from collections import Counter
from pathlib import Path

from opspilot.history.run_history import (
    find_previous_run_id,
    list_run_metadata,
    read_run_json_artifact,
)
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
    lines.extend(_render_recent_trend_section(current_run_id, runs_root, triage_records))

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

    try:
        previous_payload = read_run_json_artifact(previous_run_id, "triage_results.json", runs_root)
    except (FileNotFoundError, OSError, ValueError):
        previous_payload = None
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


def _render_recent_trend_section(
    current_run_id: str | None,
    runs_root: Path | None,
    current_triage_records: list[TriageRecord],
) -> list[str]:
    section = ["", "## Recent Trend (Last 7 Runs)"]

    trend_points = _collect_recent_high_risk_series(
        current_run_id=current_run_id,
        runs_root=runs_root,
        current_triage_records=current_triage_records,
        limit=7,
    )

    if not trend_points:
        section.append("Trend unavailable without run history context.")
        return section

    section.append("High-Risk Items (critical + high):")
    for run_id, high_risk_count in trend_points:
        section.append(f"- {run_id}: high_risk={high_risk_count}")

    if len(trend_points) == 1:
        section.append("Only current run available; additional runs are needed for trend comparison.")
        return section

    latest_count = trend_points[0][1]
    oldest_count = trend_points[-1][1]
    net_change = _format_priority_change(oldest_count, latest_count)
    section.append(f"Net change across {len(trend_points)} runs: {net_change}.")

    return section


def _collect_recent_high_risk_series(
    current_run_id: str | None,
    runs_root: Path | None,
    current_triage_records: list[TriageRecord],
    limit: int,
) -> list[tuple[str, int]]:
    if not current_run_id or runs_root is None:
        return []

    series: list[tuple[str, int]] = [
        (current_run_id, _high_risk_count_from_triage(current_triage_records))
    ]

    metadata = list_run_metadata(runs_root)
    for item in metadata:
        run_id = item.get("run_id")
        if not isinstance(run_id, str) or run_id >= current_run_id:
            continue

        try:
            payload = read_run_json_artifact(run_id, "triage_results.json", runs_root)
        except (FileNotFoundError, OSError, ValueError):
            continue
        if not isinstance(payload, list):
            continue

        series.append((run_id, _high_risk_count_from_payload(payload)))
        if len(series) >= limit:
            break

    return series


def _high_risk_count_from_triage(triage_records: list[TriageRecord]) -> int:
    return sum(1 for record in triage_records if record.urgency in {"critical", "high"})


def _high_risk_count_from_payload(payload: list[object]) -> int:
    count = 0
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        urgency = entry.get("urgency")
        if urgency in {"critical", "high"}:
            count += 1
    return count


def _format_priority_change(previous: int, current: int) -> str:
    delta = current - previous
    if delta == 0:
        return "0"
    if delta > 0:
        return f"+{delta}"
    return f"{delta}"
