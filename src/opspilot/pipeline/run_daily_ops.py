import logging
from pathlib import Path

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
from opspilot.rules.triage_rules import classify_work_item
from opspilot.utils.file_io import write_json_file, write_text_file
from opspilot.utils.logging_utils import log_event


logger = logging.getLogger("opspilot.pipeline")


def run_daily_ops(input_path: str, output_dir: str, run_date: str) -> dict[str, str]:
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

        for item in normalized_items:
            triage = classify_work_item(item)
            actions = extract_action_items(item)
            response_text = draft_suggested_response(item, triage, actions)

            triage_records.append(triage)
            action_items.extend(actions)
            suggested_responses.append(
                SuggestedResponse(work_item_id=item.id, suggested_response=response_text)
            )

        briefing = generate_daily_briefing(run_date, triage_records, action_items)

        output_path = Path(output_dir)
        triage_file = output_path / "triage_results.json"
        action_file = output_path / "action_items.json"
        response_file = output_path / "suggested_responses.json"
        briefing_file = output_path / "daily_briefing.txt"

        write_json_file(triage_file, [to_dict(record) for record in triage_records])
        write_json_file(action_file, [to_dict(action) for action in action_items])
        write_json_file(response_file, [to_dict(response) for response in suggested_responses])
        write_text_file(briefing_file, briefing)

        log_event(
            logger,
            "pipeline_complete",
            items_processed=len(normalized_items),
            triage_records=len(triage_records),
            action_items=len(action_items),
            suggested_responses=len(suggested_responses),
        )

        return {
            "triage_results": str(triage_file),
            "action_items": str(action_file),
            "suggested_responses": str(response_file),
            "daily_briefing": str(briefing_file),
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
