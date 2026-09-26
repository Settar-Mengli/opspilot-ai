"""Persist a completed file-based run into Postgres."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from opspilot.jobs.import_json import import_sample_file, upsert_run_from_metadata
from opspilot.utils.file_io import read_json_file


async def persist_run_directory(session: AsyncSession, run_dir: Path) -> str:
    """Upsert run metadata, artifacts, and triage from a history run directory."""
    metadata_path = run_dir / "run.json"
    metadata = read_json_file(metadata_path)
    if not isinstance(metadata, dict) or "run_id" not in metadata:
        raise ValueError(f"Invalid run metadata at {metadata_path}")
    return await upsert_run_from_metadata(session, metadata, run_dir)


async def persist_pipeline_outputs(
    session: AsyncSession,
    *,
    run_dir: Path,
    sample_input: Path | None = None,
) -> str:
    """Ensure work items exist (from sample if provided), then persist the run."""
    if sample_input is not None and sample_input.is_file():
        await import_sample_file(session, sample_input)
    return await persist_run_directory(session, run_dir)


def load_triage_json(path: Path) -> list[Any]:
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return payload if isinstance(payload, list) else []
