from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any

from opspilot.utils.file_io import ensure_directory, read_json_file, write_json_file, write_text_file


RUN_ID_PATTERN = re.compile(r"^run-\d{8}-\d{6}-\d{3}(?:-\d{2})?$")


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


def list_run_metadata(runs_root: Path) -> list[dict[str, Any]]:
    if not runs_root.exists() or not runs_root.is_dir():
        return []

    records: list[dict[str, Any]] = []
    for metadata_file in runs_root.rglob("run.json"):
        try:
            payload = read_json_file(metadata_file)
        except (OSError, ValueError):
            continue

        if not isinstance(payload, dict):
            continue

        records.append(dict(payload))

    records.sort(
        key=lambda item: (
            str(item.get("finished_at", "")),
            str(item.get("started_at", "")),
            str(item.get("run_id", "")),
        ),
        reverse=True,
    )
    return records


def find_run_directory(run_id: str, runs_root: Path) -> Path | None:
    if not RUN_ID_PATTERN.fullmatch(run_id):
        return None
    if not runs_root.exists() or not runs_root.is_dir():
        return None

    for run_dir in runs_root.rglob("run-*"):
        if run_dir.is_dir() and run_dir.name == run_id:
            return run_dir

    return None


def read_run_metadata(run_id: str, runs_root: Path) -> dict[str, Any] | None:
    run_dir = find_run_directory(run_id, runs_root)
    if run_dir is None:
        return None

    metadata_file = run_dir / "run.json"
    if not metadata_file.exists() or not metadata_file.is_file():
        raise FileNotFoundError("run.json not found")

    payload = read_json_file(metadata_file)
    if not isinstance(payload, dict):
        raise ValueError("run.json is not an object")

    return dict(payload)


def read_run_json_artifact(run_id: str, artifact_name: str, runs_root: Path) -> Any:
    run_dir = find_run_directory(run_id, runs_root)
    if run_dir is None:
        return None

    path = run_dir / artifact_name
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Artifact not found: {artifact_name}")

    return read_json_file(path)


def read_run_text_artifact(run_id: str, artifact_name: str, runs_root: Path) -> str | None:
    run_dir = find_run_directory(run_id, runs_root)
    if run_dir is None:
        return None

    path = run_dir / artifact_name
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Artifact not found: {artifact_name}")

    with path.open("r", encoding="utf-8") as file:
        return file.read()


def find_previous_run_id(current_run_id: str, runs_root: Path) -> str | None:
    if not RUN_ID_PATTERN.fullmatch(current_run_id):
        return None
    if not runs_root.exists() or not runs_root.is_dir():
        return None

    run_ids: list[str] = []
    for run_dir in runs_root.rglob("run-*"):
        if not run_dir.is_dir():
            continue
        run_id = run_dir.name
        if RUN_ID_PATTERN.fullmatch(run_id):
            run_ids.append(run_id)

    previous_ids = [run_id for run_id in run_ids if run_id < current_run_id]
    if not previous_ids:
        return None

    previous_ids.sort()
    return previous_ids[-1]
