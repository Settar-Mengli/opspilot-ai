"""Anthropic prepaid budget ledger (D-023 / b6.1)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from opspilot.persistence.llm_calls import record_llm_call
from opspilot.persistence.models import AnthropicPrepaidBudgetRow, LlmCallRow

BUDGET_ROW_ID = 1
ANTHROPIC_EST_INPUT_CAP = 16384
ERROR_CODE_RESERVED = "anthropic_reserved"


def get_budget(session: Session) -> AnthropicPrepaidBudgetRow | None:
    return session.get(AnthropicPrepaidBudgetRow, BUDGET_ROW_ID)


def estimate_input_tokens(*parts: str) -> int:
    """A1 estimator: max(256, utf8_bytes // 2 + 64)."""
    payload_bytes = sum(len(p.encode("utf-8")) for p in parts)
    return max(256, payload_bytes // 2 + 64)


def set_budget(
    session: Session,
    *,
    tokens: int,
    usd: Decimal,
) -> AnthropicPrepaidBudgetRow:
    """Upsert singleton ledger remaining amounts. Caller owns commit."""
    if tokens < 0 or usd < 0:
        raise ValueError("budget_amounts_must_be_non_negative")
    now = datetime.now(UTC)
    stmt = (
        pg_insert(AnthropicPrepaidBudgetRow)
        .values(
            id=BUDGET_ROW_ID,
            remaining_tokens=tokens,
            remaining_usd=usd,
            updated_at=now,
        )
        .on_conflict_do_update(
            index_elements=["id"],
            set_={
                "remaining_tokens": tokens,
                "remaining_usd": usd,
                "updated_at": now,
            },
        )
    )
    session.execute(stmt)
    session.flush()
    row = get_budget(session)
    assert row is not None
    return row


def reserve_and_open_call(
    session: Session,
    *,
    tokens: int,
    usd: Decimal,
    task: str,
    model: str,
    request_id: str | None = None,
) -> LlmCallRow | None:
    """Atomic ledger debit + open LlmCall reservation row. Caller owns commit.

    Open row uses existing status ``error`` and ``error_code=anthropic_reserved`` (B1).
    """
    if tokens < 0 or usd < 0:
        raise ValueError("reserve_amounts_must_be_non_negative")
    if get_budget(session) is None:
        return None
    now = datetime.now(UTC)
    result = session.execute(
        update(AnthropicPrepaidBudgetRow)
        .where(AnthropicPrepaidBudgetRow.id == BUDGET_ROW_ID)
        .where(AnthropicPrepaidBudgetRow.remaining_tokens >= tokens)
        .where(AnthropicPrepaidBudgetRow.remaining_usd >= usd)
        .values(
            remaining_tokens=AnthropicPrepaidBudgetRow.remaining_tokens - tokens,
            remaining_usd=AnthropicPrepaidBudgetRow.remaining_usd - usd,
            updated_at=now,
        )
        .returning(
            AnthropicPrepaidBudgetRow.remaining_tokens,
            AnthropicPrepaidBudgetRow.remaining_usd,
        )
    )
    if result.first() is None:
        session.flush()
        return None
    reservation_id = str(uuid.uuid4())
    row = record_llm_call(
        session,
        task=task,
        provider="anthropic",
        model=model,
        status="error",
        tokens_in=0,
        tokens_out=0,
        usd_estimate=usd,
        request_id=request_id,
        error_code=ERROR_CODE_RESERVED,
        meta={
            "reservation_id": reservation_id,
            "reserved_tokens": tokens,
            "reserved_usd": str(usd),
            "reconciled": False,
        },
    )
    session.flush()
    return row


def _refund(session: Session, *, tokens: int, usd: Decimal) -> None:
    now = datetime.now(UTC)
    session.execute(
        update(AnthropicPrepaidBudgetRow)
        .where(AnthropicPrepaidBudgetRow.id == BUDGET_ROW_ID)
        .values(
            remaining_tokens=AnthropicPrepaidBudgetRow.remaining_tokens + tokens,
            remaining_usd=AnthropicPrepaidBudgetRow.remaining_usd + usd,
            updated_at=now,
        )
    )


def _excess_debit_clamp(session: Session, *, tokens: int, usd: Decimal) -> None:
    now = datetime.now(UTC)
    session.execute(
        text(
            """
            UPDATE anthropic_prepaid_budget
            SET remaining_tokens = GREATEST(0, remaining_tokens - :tok),
                remaining_usd = GREATEST(0, remaining_usd - :usd),
                updated_at = :now
            WHERE id = 1
            """
        ),
        {"tok": tokens, "usd": usd, "now": now},
    )


def reconcile_reservation(
    session: Session,
    *,
    call_id: int,
    final_status: str,
    ledger_op: str,
    actual_tokens: int = 0,
    actual_usd: Decimal | None = None,
    tokens_in: int = 0,
    tokens_out: int = 0,
    error_code: str | None = None,
    extra_meta: dict[str, Any] | None = None,
) -> bool:
    """Atomic guard UPDATE + ledger op. Returns False if already reconciled (idempotent).

    ledger_op: ``refund`` (full reserved), ``keep``, ``refund_delta`` (actual ≤ reserved),
    ``excess`` (actual > reserved; clamp remaining to 0).
    """
    row = session.execute(select(LlmCallRow).where(LlmCallRow.id == call_id).with_for_update()).scalar_one_or_none()
    if row is None or row.provider != "anthropic":
        return False
    meta = dict(row.meta or {})
    if meta.get("reconciled") is True:
        return False

    reserved_tokens = int(meta.get("reserved_tokens") or 0)
    reserved_usd = Decimal(str(meta.get("reserved_usd") or "0"))
    meta["reconciled"] = True
    if extra_meta:
        meta.update(extra_meta)

    if ledger_op == "refund":
        _refund(session, tokens=reserved_tokens, usd=reserved_usd)
        row.usd_estimate = Decimal(0)
    elif ledger_op == "keep":
        row.usd_estimate = reserved_usd
    elif ledger_op == "refund_delta":
        if actual_usd is None:
            raise ValueError("actual_usd_required")
        tok_delta = max(0, reserved_tokens - actual_tokens)
        usd_delta = reserved_usd - actual_usd
        if usd_delta < 0:
            usd_delta = Decimal(0)
        if tok_delta > 0 or usd_delta > 0:
            _refund(session, tokens=tok_delta, usd=usd_delta)
        row.usd_estimate = actual_usd
    elif ledger_op == "excess":
        if actual_usd is None:
            raise ValueError("actual_usd_required")
        tok_over = max(0, actual_tokens - reserved_tokens)
        usd_over = actual_usd - reserved_usd
        if usd_over < 0:
            usd_over = Decimal(0)
        if tok_over > 0 or usd_over > 0:
            _excess_debit_clamp(session, tokens=tok_over, usd=usd_over)
        meta["reservation_underestimate"] = True
        row.usd_estimate = actual_usd
    else:
        raise ValueError(f"unknown_ledger_op:{ledger_op}")

    row.status = final_status
    row.tokens_in = tokens_in
    row.tokens_out = tokens_out
    row.error_code = error_code
    row.meta = meta
    session.flush()
    return True


def anthropic_call_counts(session: Session) -> dict[str, Any]:
    """Counts-only summary for CLI show (B3)."""
    total = session.scalar(select(func.count()).select_from(LlmCallRow).where(LlmCallRow.provider == "anthropic"))
    by_status_rows = session.execute(
        select(LlmCallRow.status, func.count()).where(LlmCallRow.provider == "anthropic").group_by(LlmCallRow.status)
    ).all()
    by_task_rows = session.execute(
        select(LlmCallRow.task, func.count()).where(LlmCallRow.provider == "anthropic").group_by(LlmCallRow.task)
    ).all()
    max_id = session.scalar(select(func.max(LlmCallRow.id)).where(LlmCallRow.provider == "anthropic"))
    return {
        "anthropic_rows_total": int(total or 0),
        "by_status": {str(s): int(c) for s, c in by_status_rows},
        "by_task": {str(t): int(c) for t, c in by_task_rows},
        "max_id": int(max_id) if max_id is not None else None,
    }
