"""In-process pipeline runner shared by legacy and v1 routes."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from pathlib import Path

from opspilot.api.paths import API_OUTPUT_DIR, RUN_TIMEOUT_SECONDS
from opspilot.api.schemas import RunPipelineRequest, resolve_input_file, safe_error
from opspilot.models.schemas import OpsPilotError
from opspilot.pipeline.run_daily_ops import run_daily_ops

logger = logging.getLogger("opspilot.api.pipeline")


def execute_pipeline(req: RunPipelineRequest) -> dict[str, str]:
    """Run the daily ops pipeline; returns output path map including run_id."""
    input_path = resolve_input_file(req.input_file)
    if not input_path.exists():
        raise safe_error(404, "input_not_found", f"Input file not found: {req.input_file}")

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(
                run_daily_ops,
                str(input_path),
                str(API_OUTPUT_DIR),
                req.date.isoformat(),
            )
            return future.result(timeout=RUN_TIMEOUT_SECONDS)
    except FuturesTimeoutError:
        logger.error(
            "pipeline_run_timeout",
            extra={"timeout_seconds": RUN_TIMEOUT_SECONDS, "input_file": req.input_file},
        )
        raise safe_error(504, "pipeline_timeout", "Pipeline run timed out.") from None
    except OpsPilotError as exc:
        logger.error(
            "pipeline_run_failed",
            extra={
                "input_file": req.input_file,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            },
        )
        raise safe_error(500, "pipeline_failed", "Pipeline execution failed.") from exc
    except Exception as exc:
        logger.error(
            "pipeline_run_failed",
            extra={
                "input_file": req.input_file,
                "error_type": type(exc).__name__,
                "error_message": str(exc)[:1000],
            },
        )
        raise safe_error(500, "pipeline_failed", "Pipeline execution failed.") from exc


def history_dir_from_outputs(outputs: dict[str, str]) -> Path:
    history = outputs.get("history_dir")
    if history:
        return Path(history)
    raise safe_error(500, "pipeline_failed", "Pipeline execution failed.")
