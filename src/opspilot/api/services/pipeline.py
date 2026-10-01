"""In-process pipeline runner for /api/v1 (Postgres-only; no file writes)."""

from __future__ import annotations

import contextvars
import logging
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import Any

from opspilot.api.paths import RUN_TIMEOUT_SECONDS
from opspilot.api.schemas import RunPipelineRequest, resolve_input_file, safe_error
from opspilot.models.schemas import OpsPilotError
from opspilot.pipeline.run_daily_ops import PipelineResult, run_pipeline

logger = logging.getLogger("opspilot.api.pipeline")


def execute_pipeline(
    req: RunPipelineRequest,
    *,
    raw_items: list[dict[str, Any]] | None = None,
) -> PipelineResult:
    """Run the daily ops pipeline in-memory (no filesystem artifacts).

    When ``raw_items`` is set (Google-connected DB ingest), skip the sample file.
    """
    input_path = resolve_input_file(req.input_file)
    if raw_items is None and not input_path.exists():
        raise safe_error(404, "input_not_found", f"Input file not found: {req.input_file}")

    try:
        # A2: ContextVars do not propagate into ThreadPoolExecutor workers;
        # copy the request context (incl. request_id) into the worker thread.
        ctx = contextvars.copy_context()

        def _call() -> PipelineResult:
            return run_pipeline(str(input_path), req.date.isoformat(), raw_items=raw_items)

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(ctx.run, _call)
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
