"""Repository helpers for LlmCall metering rows."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from opspilot.persistence.models import LlmCallRow


def record_llm_call(
    session: Session,
    *,
    task: str,
    provider: str,
    model: str,
    status: str,
    latency_ms: int | None = None,
    ttft_ms: int | None = None,
    tokens_in: int = 0,
    tokens_out: int = 0,
    usd_estimate: Decimal | None = None,
    prompt_version: str | None = None,
    request_id: str | None = None,
    run_id: str | None = None,
    work_item_id: str | None = None,
    error_code: str | None = None,
    meta: dict[str, Any] | None = None,
) -> LlmCallRow:
    """Insert one attempt row. Caller owns commit."""
    row = LlmCallRow(
        task=task,
        provider=provider,
        model=model,
        status=status,
        latency_ms=latency_ms,
        ttft_ms=ttft_ms,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        usd_estimate=usd_estimate,
        prompt_version=prompt_version,
        request_id=request_id,
        run_id=run_id,
        work_item_id=work_item_id,
        error_code=error_code,
        meta=meta or {},
    )
    session.add(row)
    session.flush()
    return row
