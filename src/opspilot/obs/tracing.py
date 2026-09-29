"""OTel-compatible + JSONL tracing hooks for LLM attempts (D-019)."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_TRACE_DIR = Path("data/llm_traces")


@dataclass(frozen=True, slots=True)
class LlmSpanAttrs:
    """gen_ai.* style attributes (no prompt bodies / secrets)."""

    task: str
    provider: str
    model: str
    status: str
    latency_ms: int | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    request_id: str | None = None
    error_code: str | None = None


def emit_llm_span(attrs: LlmSpanAttrs, *, extra: dict[str, Any] | None = None) -> None:
    """Emit a structured log span (OTel exporter deferred; JSON attrs for collectors)."""
    payload: dict[str, Any] = {
        "gen_ai.operation.name": "chat",
        "gen_ai.request.model": attrs.model,
        "gen_ai.system": attrs.provider,
        "gen_ai.usage.input_tokens": attrs.tokens_in,
        "gen_ai.usage.output_tokens": attrs.tokens_out,
        "opspilot.task": attrs.task,
        "opspilot.status": attrs.status,
    }
    if attrs.latency_ms is not None:
        payload["opspilot.latency_ms"] = attrs.latency_ms
    if attrs.request_id:
        payload["opspilot.request_id"] = attrs.request_id
    if attrs.error_code:
        payload["opspilot.error_code"] = attrs.error_code
    if extra:
        payload.update(extra)
    logger.info("llm.span %s", json.dumps(payload, sort_keys=True, default=str))


def append_llm_jsonl(attrs: LlmSpanAttrs, *, directory: Path | None = None) -> Path | None:
    """Append one JSONL record under data/llm_traces/ (or stdout path when CI).

    Returns the file written, or None when JSONL is disabled via OPSPILOT_LLM_JSONL=0.
    """
    if os.environ.get("OPSPILOT_LLM_JSONL", "1").strip().lower() in {"0", "false", "no", "off"}:
        return None

    if os.environ.get("CI", "").strip().lower() in {"1", "true", "yes"}:
        # CI: keep on stdout via emit_llm_span only; skip disk.
        emit_llm_span(attrs)
        return None

    root = directory or Path(os.environ.get("OPSPILOT_LLM_TRACE_DIR", str(_DEFAULT_TRACE_DIR)))
    root.mkdir(parents=True, exist_ok=True)
    day = datetime.now(UTC).strftime("%Y-%m-%d")
    path = root / f"llm-{day}.jsonl"
    record = {
        "ts": datetime.now(UTC).isoformat(),
        **asdict(attrs),
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True, default=str) + "\n")
    return path
