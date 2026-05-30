from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from opspilot.utils.file_io import ensure_directory, write_json_file, write_text_file


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def generate_run_id(started_at: datetime) -> str:
    millis = started_at.microsecond // 1000
    return f"run-{started_at:%Y%m%d-%H%M%S}-{millis:03d}"


def history_runs_root(output_dir: Path) -> Path:
    data_root = output_dir.parent
    return data_root / "history" / "runs"


def create_run_directory(runs_root: Path, started_at: datetime, run_id: str) -> Path:
    day_dir = runs_root / f"{started_at:%Y}" / f"{started_at:%m}" / f"{started_at:%d}"
    ensure_directory(day_dir)

    candidate = day_dir / run_id
    suffix = 1
    while candidate.exists():
        candidate = day_dir / f"{run_id}-{suffix:02d}"
        suffix += 1

    candidate.mkdir(parents=True, exist_ok=False)
    return candidate


def write_run_artifacts(
    run_dir: Path,
    triage_payload: list[dict[str, Any]],
    action_payload: list[dict[str, Any]],
    response_payload: list[dict[str, Any]],
    briefing_text: str,
) -> dict[str, str]:
    triage_name = "triage_results.json"
    action_name = "action_items.json"
    response_name = "suggested_responses.json"
    briefing_name = "daily_briefing.txt"

    write_json_file(run_dir / triage_name, triage_payload)
    write_json_file(run_dir / action_name, action_payload)
    write_json_file(run_dir / response_name, response_payload)
    write_text_file(run_dir / briefing_name, briefing_text)

    return {
        "triage_results": triage_name,
        "action_items": action_name,
        "suggested_responses": response_name,
        "daily_briefing": briefing_name,
    }


def write_run_metadata(run_dir: Path, metadata: dict[str, Any]) -> None:
    write_json_file(run_dir / "run.json", metadata)
