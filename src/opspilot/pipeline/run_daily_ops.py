"""Daily ops pipeline — CLI writes files; API uses in-memory result + Postgres."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from opspilot.adapters.briefing_adapter import generate_ai_briefing
from opspilot.adapters.factory import get_adapter
from opspilot.history.run_history import (
    create_run_directory,
    generate_run_id,
    history_runs_root,
    to_iso_utc,
    utc_now,
    write_run_artifacts,
    write_run_metadata,
)
from opspilot.ingest.loader import load_raw_items
from opspilot.ingest.normalizer import normalize_items
from opspilot.models.schemas import (
    InputValidationError,
    PipelineExecutionError,
    SuggestedResponse,
    to_dict,
)
from opspilot.nlp.action_extractor import extract_action_items
from opspilot.nlp.briefing_generator import generate_daily_briefing
from opspilot.nlp.response_drafter import draft_suggested_response
from opspilot.services._llm import llm_session_scope
from opspilot.utils.file_io import write_json_file, write_text_file
from opspilot.utils.logging_utils import log_event

load_dotenv()

logger = logging.getLogger("opspilot.pipeline")


@dataclass(frozen=True)
class PipelineResult:
    """In-memory pipeline outputs for API → Postgres persistence (no files)."""

    run_id: str
    metadata: dict[str, Any]
    artifacts: dict[str, tuple[str, str]]  # name -> (content_type, content)
    work_items: list[dict[str, Any]]


def run_pipeline(
    input_path: str,
    run_date: str,
    *,
    runs_root: Path | None = None,
    raw_items: list[dict[str, Any]] | None = None,
) -> PipelineResult:
    """Execute triage/briefing pipeline without writing files.

    When ``raw_items`` is provided, skip file load and triage those dicts instead.
    """
    started_at = utc_now()
    source_label = input_path if raw_items is None else "db:gmail"
    log_event(logger, "pipeline_start", input_path=source_label, run_date=run_date)

    try:
        loaded = raw_items if raw_items is not None else load_raw_items(input_path)
        normalized_items = normalize_items(loaded)

        triage_records = []
        action_items = []
        suggested_responses = []

        with llm_session_scope() as llm_session:
            adapter = get_adapter(session=llm_session)
            for item in normalized_items:
                triage = adapter.classify(item)
                actions = extract_action_items(item)
                response_text = draft_suggested_response(item, triage, actions)
                triage_records.append(triage)
                action_items.extend(actions)
                suggested_responses.append(SuggestedResponse(work_item_id=item.id, suggested_response=response_text))

            run_id = generate_run_id(started_at)
            briefing = generate_daily_briefing(
                run_date,
                triage_records,
                action_items,
                normalized_items,
                current_run_id=run_id,
                runs_root=runs_root,
            )
            triage_payload = [to_dict(record) for record in triage_records]
            action_payload = [to_dict(action) for action in action_items]
            response_payload = [to_dict(response) for response in suggested_responses]
            ai_briefing = generate_ai_briefing(
                run_date,
                triage_records,
                action_items,
                normalized_items,
                briefing,
                session=llm_session,
            )

        finished_at = utc_now()
        duration_ms = int((finished_at - started_at).total_seconds() * 1000)
        artifact_names = {
            "triage_results": "triage_results.json",
            "action_items": "action_items.json",
            "suggested_responses": "suggested_responses.json",
            "daily_briefing": "daily_briefing.txt",
            "ai_briefing": "ai_briefing.txt",
        }
        metadata = {
            "run_id": run_id,
            "started_at": to_iso_utc(started_at),
            "finished_at": to_iso_utc(finished_at),
            "duration_ms": duration_ms,
            "status": "success",
            "input_file": source_label,
            "item_count": len(normalized_items),
            "triage_count": len(triage_records),
            "action_count": len(action_items),
            "suggested_response_count": len(suggested_responses),
            "artifacts": artifact_names,
            "error": None,
        }
        artifacts: dict[str, tuple[str, str]] = {
            "triage_results": ("json", json.dumps(triage_payload, indent=2)),
            "action_items": ("json", json.dumps(action_payload, indent=2)),
            "suggested_responses": ("json", json.dumps(response_payload, indent=2)),
            "daily_briefing": ("text", briefing),
            "ai_briefing": ("text", ai_briefing),
        }
        work_items = [to_dict(item) for item in normalized_items]
        log_event(
            logger,
            "pipeline_complete",
            items_processed=len(normalized_items),
            triage_records=len(triage_records),
            action_items=len(action_items),
            suggested_responses=len(suggested_responses),
            run_id=run_id,
        )
        return PipelineResult(run_id=run_id, metadata=metadata, artifacts=artifacts, work_items=work_items)
    except InputValidationError:
        log_event(logger, "pipeline_validation_failed", input_path=source_label)
        raise
    except Exception as exc:
        log_event(logger, "pipeline_failed", error_type=type(exc).__name__, message=str(exc))
        raise PipelineExecutionError("Pipeline execution failed") from exc


def run_daily_ops(input_path: str, output_dir: str, run_date: str) -> dict[str, str]:
    """CLI export path: run pipeline and write artifacts under output_dir (no Postgres)."""
    output_path = Path(output_dir)
    runs_root = history_runs_root(output_path)
    # Pipeline first: failed validation must not create output/history dirs (hermetic E1).
    result = run_pipeline(input_path, run_date, runs_root=runs_root)
    output_path.mkdir(parents=True, exist_ok=True)

    triage_file = output_path / "triage_results.json"
    action_file = output_path / "action_items.json"
    response_file = output_path / "suggested_responses.json"
    briefing_file = output_path / "daily_briefing.txt"
    ai_briefing_file = output_path / "ai_briefing.txt"

    write_json_file(triage_file, json.loads(result.artifacts["triage_results"][1]))
    write_json_file(action_file, json.loads(result.artifacts["action_items"][1]))
    write_json_file(response_file, json.loads(result.artifacts["suggested_responses"][1]))
    write_text_file(briefing_file, result.artifacts["daily_briefing"][1])
    write_text_file(ai_briefing_file, result.artifacts["ai_briefing"][1])

    started = datetime.fromisoformat(result.metadata["started_at"].replace("Z", "+00:00"))
    run_dir = create_run_directory(runs_root, started, result.run_id)
    artifacts = write_run_artifacts(
        run_dir=run_dir,
        triage_payload=json.loads(result.artifacts["triage_results"][1]),
        action_payload=json.loads(result.artifacts["action_items"][1]),
        response_payload=json.loads(result.artifacts["suggested_responses"][1]),
        briefing_text=result.artifacts["daily_briefing"][1],
    )
    write_text_file(run_dir / "ai_briefing.txt", result.artifacts["ai_briefing"][1])
    metadata = dict(result.metadata)
    metadata["output_dir"] = str(output_path)
    metadata["history_dir"] = str(run_dir)
    metadata["artifacts"] = {**artifacts, "ai_briefing": "ai_briefing.txt"}
    write_run_metadata(run_dir, metadata)

    return {
        "triage_results": str(triage_file),
        "action_items": str(action_file),
        "suggested_responses": str(response_file),
        "daily_briefing": str(briefing_file),
        "run_id": result.run_id,
        "history_dir": str(run_dir),
    }
