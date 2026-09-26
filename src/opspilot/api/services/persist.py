"""Persist pipeline results into Postgres (sync)."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from opspilot.jobs.import_json import (
    import_sample_file,
    upsert_run_from_contents,
    upsert_run_from_metadata,
    upsert_work_items,
)
from opspilot.pipeline.run_daily_ops import PipelineResult
from opspilot.utils.file_io import read_json_file


def persist_run_directory(session: Session, run_dir: Path) -> str:
    """Upsert run metadata, artifacts, and triage from a history run directory."""
    metadata_path = run_dir / "run.json"
    metadata = read_json_file(metadata_path)
    if not isinstance(metadata, dict) or "run_id" not in metadata:
        raise ValueError(f"Invalid run metadata at {metadata_path}")
    return upsert_run_from_metadata(session, metadata, run_dir)


def persist_pipeline_result(
    session: Session,
    result: PipelineResult,
    *,
    sample_input: Path | None = None,
) -> str:
    """Persist an in-memory pipeline result (API path; no files written)."""
    if sample_input is not None and sample_input.is_file():
        import_sample_file(session, sample_input)
    elif result.work_items:
        upsert_work_items(session, result.work_items)
    return upsert_run_from_contents(session, result.metadata, result.artifacts)
