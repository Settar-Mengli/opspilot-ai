"""Import sample work items and history runs into Postgres (X5).

Usage:
  uv run python -m opspilot.jobs.import_json data/raw/sample_input.json
  uv run python -m opspilot.jobs.import_json --history data/history/runs
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from opspilot.persistence.db import create_engine, create_session_factory, get_database_url
from opspilot.persistence.models import RunArtifactRow, RunRow, TriageDecisionRow, WorkItemRow

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SAMPLE = PROJECT_ROOT / "data" / "raw" / "sample_input.json"
DEFAULT_HISTORY = PROJECT_ROOT / "data" / "history" / "runs"


async def upsert_work_items(session: AsyncSession, items: list[dict[str, Any]]) -> int:
    if not items:
        return 0
    rows = []
    for raw in items:
        rows.append(
            {
                "id": str(raw["id"]),
                "source_type": str(raw["source_type"]),
                "subject_or_title": str(raw["subject_or_title"]),
                "body_or_description": str(raw["body_or_description"]),
                "sender_or_requester": str(raw["sender_or_requester"]),
                "received_at": str(raw["received_at"]),
                "tags": list(raw.get("tags") or []),
            }
        )
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
    await session.execute(stmt)
    return len(rows)


async def upsert_run_from_metadata(
    session: AsyncSession, metadata: dict[str, Any], run_dir: Path
) -> str:
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
    await session.execute(stmt)

    artifacts = metadata.get("artifacts") or {}
    if isinstance(artifacts, dict):
        for logical_name, filename in artifacts.items():
            if not isinstance(filename, str):
                continue
            path = run_dir / filename
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            content_type = "json" if filename.endswith(".json") else "text"
            art = pg_insert(RunArtifactRow).values(
                {
                    "run_id": run_id,
                    "name": str(logical_name),
                    "content_type": content_type,
                    "content": text,
                }
            )
            art = art.on_conflict_do_update(
                constraint="uq_run_artifacts_run_name",
                set_={
                    "content_type": art.excluded.content_type,
                    "content": art.excluded.content,
                },
            )
            await session.execute(art)

            if logical_name == "triage_results" and content_type == "json":
                await _upsert_triage_from_json(session, run_id, text)

    return run_id


async def _upsert_triage_from_json(session: AsyncSession, run_id: str, text: str) -> None:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return
    if not isinstance(payload, list):
        return

    existing_ids = set(
        (
            await session.execute(select(WorkItemRow.id))
        ).scalars().all()
    )

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
        await session.execute(stmt)


async def import_sample_file(session: AsyncSession, path: Path) -> int:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Expected JSON array in {path}")
    return await upsert_work_items(session, payload)


async def import_history_runs(session: AsyncSession, runs_root: Path) -> int:
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
        await upsert_run_from_metadata(session, metadata, metadata_file.parent)
        count += 1
    return count


async def count_work_items(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.count()).select_from(WorkItemRow)) or 0)


async def count_runs(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.count()).select_from(RunRow)) or 0)


async def run_import(
    *,
    sample_path: Path | None,
    history_root: Path | None,
    database_url: str | None = None,
) -> dict[str, int]:
    engine = create_engine(database_url or get_database_url())
    factory = create_session_factory(engine)
    result = {"work_items": 0, "runs": 0}
    async with factory() as session:
        if sample_path is not None:
            result["work_items"] = await import_sample_file(session, sample_path)
        if history_root is not None and history_root.is_dir():
            result["runs"] = await import_history_runs(session, history_root)
        await session.commit()
        result["work_item_count"] = await count_work_items(session)
        result["run_count"] = await count_runs(session)
    await engine.dispose()
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

    if sys.platform == "win32":
        import asyncio as _asyncio

        _asyncio.set_event_loop_policy(_asyncio.WindowsSelectorEventLoopPolicy())

    stats = asyncio.run(
        run_import(sample_path=sample_path, history_root=history_root)
    )
    print(
        f"Imported work_items_upserted={stats['work_items']} "
        f"runs_upserted={stats['runs']} "
        f"work_item_count={stats['work_item_count']} "
        f"run_count={stats['run_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
