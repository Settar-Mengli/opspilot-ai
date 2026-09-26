"""Sync variants of X5 import helpers for the FastAPI path (Windows-safe)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from opspilot.persistence.models import RunArtifactRow, RunRow, TriageDecisionRow, WorkItemRow


def upsert_work_items_sync(session: Session, items: list[dict[str, Any]]) -> int:
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


def import_sample_file_sync(session: Session, path: Path) -> int:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Expected JSON array in {path}")
    return upsert_work_items_sync(session, payload)


def upsert_run_from_metadata_sync(session: Session, metadata: dict[str, Any], run_dir: Path) -> str:
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
            session.execute(art)
            if logical_name == "triage_results" and content_type == "json":
                _upsert_triage_from_json_sync(session, run_id, text)
    return run_id


def _upsert_triage_from_json_sync(session: Session, run_id: str, text: str) -> None:
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
