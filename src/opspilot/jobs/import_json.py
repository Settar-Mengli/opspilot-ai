"""Import sample work items and history runs into Postgres (X5, sync).

Usage:
  uv run python -m opspilot.jobs.import_json data/raw/sample_input.json
  uv run python -m opspilot.jobs.import_json --history data/history/runs
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from opspilot.persistence.db import create_engine, create_session_factory, get_database_url
from opspilot.persistence.models import RunArtifactRow, RunRow, TriageDecisionRow, WorkItemRow

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SAMPLE = PROJECT_ROOT / "data" / "raw" / "sample_input.json"
DEFAULT_HISTORY = PROJECT_ROOT / "data" / "history" / "runs"


def upsert_work_items(session: Session, items: list[dict[str, Any]]) -> int:
    if not items:
        return 0
    rows = [
        {
            "id": str(raw["id"]),
            "source_type": str(raw["source_type"]),
            "subject_or_title": str(raw["subject_or_title"]),
            "body_or_description": str(raw["body_or_description"]),
            "sender_or_requester": str(raw["sender_or_requester"]),
            "received_at": str(raw["received_at"]),
            "tags": list(raw.get("tags") or []),
        }
        for raw in items
    ]
    stmt = pg_insert(WorkItemRow).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[WorkItemRow.id],
        set_={
            "source_type": stmt.excluded.source_type,
            "subject_or_title": stmt.excluded.subject_or_title,
            "body_or_description": stmt.excluded.body_or_description,
            "sender_or_requester": stmt.excluded.sender_or_requester,
            "received_at": stmt.excluded.received_at,
            "tags": stmt.excluded.tags,
        },
    )
    session.execute(stmt)
    return len(rows)


def upsert_run_from_metadata(session: Session, metadata: dict[str, Any], run_dir: Path) -> str:
    run_id = str(metadata["run_id"])
    _upsert_run_row(session, metadata)
    artifacts = metadata.get("artifacts") or {}
    run_root = run_dir.resolve()
    if isinstance(artifacts, dict):
        for logical_name, filename in artifacts.items():
            if not isinstance(filename, str):
                continue
            path = (run_dir / filename).resolve()
            try:
                path.relative_to(run_root)
            except ValueError:
                continue
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            content_type = "json" if filename.endswith(".json") else "text"
            _upsert_artifact(session, run_id, str(logical_name), content_type, text)
            if logical_name == "triage_results" and content_type == "json":
                _upsert_triage_from_json(session, run_id, text)
    return run_id


def upsert_run_from_contents(
    session: Session,
    metadata: dict[str, Any],
    artifacts: dict[str, tuple[str, str]],
) -> str:
    """Persist a run from in-memory artifact contents (API path; no files)."""
    run_id = str(metadata["run_id"])
    _upsert_run_row(session, metadata)
    for logical_name, (content_type, content) in artifacts.items():
        _upsert_artifact(session, run_id, logical_name, content_type, content)
        if logical_name == "triage_results" and content_type == "json":
            _upsert_triage_from_json(session, run_id, content)
    return run_id


def _upsert_run_row(session: Session, metadata: dict[str, Any]) -> None:
    run_id = str(metadata["run_id"])
    stmt = pg_insert(RunRow).values(
        {
            "run_id": run_id,
            "started_at": metadata.get("started_at"),
            "finished_at": metadata.get("finished_at"),
            "duration_ms": metadata.get("duration_ms"),
            "status": str(metadata.get("status") or "success"),
            "input_file": metadata.get("input_file"),
            "item_count": metadata.get("item_count"),
            "triage_count": metadata.get("triage_count"),
            "metadata_json": dict(metadata),
        }
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[RunRow.run_id],
        set_={
            "started_at": stmt.excluded.started_at,
            "finished_at": stmt.excluded.finished_at,
            "duration_ms": stmt.excluded.duration_ms,
            "status": stmt.excluded.status,
            "input_file": stmt.excluded.input_file,
            "item_count": stmt.excluded.item_count,
            "triage_count": stmt.excluded.triage_count,
            "metadata_json": stmt.excluded.metadata_json,
        },
    )
    session.execute(stmt)


def _upsert_artifact(session: Session, run_id: str, name: str, content_type: str, content: str) -> None:
    art = pg_insert(RunArtifactRow).values(
        {
            "run_id": run_id,
            "name": name,
            "content_type": content_type,
            "content": content,
        }
    )
    art = art.on_conflict_do_update(
        constraint="uq_run_artifacts_run_name",
        set_={
            "content_type": art.excluded.content_type,
            "content": art.excluded.content,
        },
    )
    session.execute(art)


def _upsert_triage_from_json(session: Session, run_id: str, text: str) -> None:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return
    if not isinstance(payload, list):
        return
    existing_ids = set(session.execute(select(WorkItemRow.id)).scalars().all())
    for record in payload:
        if not isinstance(record, dict):
            continue
        work_item_id = str(record.get("id") or "")
        if not work_item_id or work_item_id not in existing_ids:
            continue
        stmt = pg_insert(TriageDecisionRow).values(
            {
                "work_item_id": work_item_id,
                "run_id": run_id,
                "urgency": str(record.get("urgency") or "low"),
                "urgency_reason": str(record.get("urgency_reason") or ""),
                "category": str(record.get("category") or "other"),
                "category_reason": str(record.get("category_reason") or ""),
                "sentiment": str(record.get("sentiment") or "neutral"),
                "sentiment_reason": str(record.get("sentiment_reason") or ""),
            }
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_triage_work_item_run",
            set_={
                "urgency": stmt.excluded.urgency,
                "urgency_reason": stmt.excluded.urgency_reason,
                "category": stmt.excluded.category,
                "category_reason": stmt.excluded.category_reason,
                "sentiment": stmt.excluded.sentiment,
                "sentiment_reason": stmt.excluded.sentiment_reason,
            },
        )
        session.execute(stmt)


def import_sample_file(session: Session, path: Path) -> int:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Expected JSON array in {path}")
    return upsert_work_items(session, payload)


def import_history_runs(session: Session, runs_root: Path) -> int:
    if not runs_root.is_dir():
        return 0
    count = 0
    for metadata_file in sorted(runs_root.rglob("run.json")):
        try:
            metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(metadata, dict) or "run_id" not in metadata:
            continue
        upsert_run_from_metadata(session, metadata, metadata_file.parent)
        count += 1
    return count


def count_work_items(session: Session) -> int:
    return int(session.scalar(select(func.count()).select_from(WorkItemRow)) or 0)


def count_runs(session: Session) -> int:
    return int(session.scalar(select(func.count()).select_from(RunRow)) or 0)


def run_import(
    *,
    sample_path: Path | None,
    history_root: Path | None,
    database_url: str | None = None,
) -> dict[str, int]:
    engine = create_engine(database_url or get_database_url())
    factory = create_session_factory(engine)
    result: dict[str, int] = {"work_items": 0, "runs": 0}
    with factory() as session:
        if sample_path is not None:
            result["work_items"] = import_sample_file(session, sample_path)
        if history_root is not None and history_root.is_dir():
            result["runs"] = import_history_runs(session, history_root)
        session.commit()
        result["work_item_count"] = count_work_items(session)
        result["run_count"] = count_runs(session)
    engine.dispose()
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import JSON sample/history into Postgres")
    parser.add_argument(
        "sample",
        nargs="?",
        default=str(DEFAULT_SAMPLE),
        help="Path to sample_input.json (default: data/raw/sample_input.json)",
    )
    parser.add_argument(
        "--history",
        default=str(DEFAULT_HISTORY),
        help="Path to history runs root (default: data/history/runs)",
    )
    parser.add_argument(
        "--no-history",
        action="store_true",
        help="Skip history import",
    )
    args = parser.parse_args(argv)

    sample_path = Path(args.sample)
    history_root = None if args.no_history else Path(args.history)

    if not sample_path.is_file():
        print(f"Error: sample file not found: {sample_path}", file=sys.stderr)
        return 1

    stats = run_import(sample_path=sample_path, history_root=history_root)
    print(
        f"Imported work_items_upserted={stats['work_items']} "
        f"runs_upserted={stats['runs']} "
        f"work_item_count={stats['work_item_count']} "
        f"run_count={stats['run_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
