import logging
from pathlib import Path

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
from opspilot.utils.file_io import write_json_file, write_text_file
from opspilot.utils.logging_utils import log_event

load_dotenv()


logger = logging.getLogger("opspilot.pipeline")


def run_daily_ops(input_path: str, output_dir: str, run_date: str) -> dict[str, str]:
    started_at = utc_now()

    log_event(
        logger,
        "pipeline_start",
        input_path=input_path,
        output_dir=output_dir,
        run_date=run_date,
    )

    try:
        raw_items = load_raw_items(input_path)
        normalized_items = normalize_items(raw_items)

        triage_records = []
        action_items = []
        suggested_responses = []

        adapter = get_adapter()
        for item in normalized_items:
            triage = adapter.classify(item)
            actions = extract_action_items(item)
            response_text = draft_suggested_response(item, triage, actions)

            triage_records.append(triage)
            action_items.extend(actions)
            suggested_responses.append(
                SuggestedResponse(work_item_id=item.id, suggested_response=response_text)
            )

        output_path = Path(output_dir)
        run_id = generate_run_id(started_at)
        runs_root = history_runs_root(output_path)
        briefing = generate_daily_briefing(
            run_date,
            triage_records,
            action_items,
            normalized_items,
            current_run_id=run_id,
            runs_root=runs_root,
        )

        triage_file = output_path / "triage_results.json"
        action_file = output_path / "action_items.json"
        response_file = output_path / "suggested_responses.json"
        briefing_file = output_path / "daily_briefing.txt"

        triage_payload = [to_dict(record) for record in triage_records]
        action_payload = [to_dict(action) for action in action_items]
        response_payload = [to_dict(response) for response in suggested_responses]

        write_json_file(triage_file, triage_payload)
        write_json_file(action_file, action_payload)
        write_json_file(response_file, response_payload)
        write_text_file(briefing_file, briefing)

        ai_briefing = generate_ai_briefing(
            run_date, triage_records, action_items, normalized_items, briefing
        )
        ai_briefing_file = output_path / "ai_briefing.txt"
        write_text_file(ai_briefing_file, ai_briefing)

        run_dir = create_run_directory(runs_root, started_at, run_id)
        artifacts = write_run_artifacts(
            run_dir=run_dir,
            triage_payload=triage_payload,
            action_payload=action_payload,
            response_payload=response_payload,
            briefing_text=briefing,
        )
        write_text_file(run_dir / "ai_briefing.txt", ai_briefing)

        finished_at = utc_now()
        duration_ms = int((finished_at - started_at).total_seconds() * 1000)
        metadata = {
            "run_id": run_dir.name,
            "started_at": to_iso_utc(started_at),
            "finished_at": to_iso_utc(finished_at),
            "duration_ms": duration_ms,
            "status": "success",
            "input_file": input_path,
            "output_dir": str(output_path),
            "history_dir": str(run_dir),
            "item_count": len(normalized_items),
            "triage_count": len(triage_records),
            "action_count": len(action_items),
            "suggested_response_count": len(suggested_responses),
            "artifacts": artifacts,
            "error": None,
        }
        write_run_metadata(run_dir, metadata)

        log_event(
            logger,
            "pipeline_complete",
            items_processed=len(normalized_items),
            triage_records=len(triage_records),
            action_items=len(action_items),
            suggested_responses=len(suggested_responses),
            run_id=run_dir.name,
        )

        return {
            "triage_results": str(triage_file),
            "action_items": str(action_file),
            "suggested_responses": str(response_file),
            "daily_briefing": str(briefing_file),
            "run_id": run_dir.name,
            "history_dir": str(run_dir),
        }
    except InputValidationError:
        log_event(logger, "pipeline_validation_failed", input_path=input_path)
        raise
    except Exception as exc:
        log_event(
            logger,
            "pipeline_failed",
            error_type=type(exc).__name__,
            message=str(exc),
        )
        raise PipelineExecutionError("Pipeline execution failed") from exc
