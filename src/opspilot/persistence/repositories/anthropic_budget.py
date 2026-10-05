"""Anthropic prepaid budget ledger (D-023 / B6 plumbing)."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from opspilot.persistence.models import AnthropicPrepaidBudgetRow

BUDGET_ROW_ID = 1


def get_budget(session: Session) -> AnthropicPrepaidBudgetRow | None:
    return session.get(AnthropicPrepaidBudgetRow, BUDGET_ROW_ID)


def _env_seed_amounts() -> tuple[int, Decimal] | None:
    raw_tok = os.environ.get("OPSPILOT_ANTHROPIC_BUDGET_TOKENS")
    raw_usd = os.environ.get("OPSPILOT_ANTHROPIC_BUDGET_USD")
    if raw_tok is None or not raw_tok.strip() or raw_usd is None or not raw_usd.strip():
        return None
    try:
        tok = int(raw_tok.strip())
        usd = Decimal(raw_usd.strip())
    except (ValueError, InvalidOperation):
        return None
    if tok <= 0 or usd <= 0:
        return None
    return tok, usd


def seed_from_env_if_missing(session: Session) -> bool:
    """Insert singleton row from env on first debit; never overwrite an existing row."""
    if get_budget(session) is not None:
        return True
    amounts = _env_seed_amounts()
    if amounts is None:
        return False
    tok, usd = amounts
    now = datetime.now(UTC)
    stmt = (
        pg_insert(AnthropicPrepaidBudgetRow)
        .values(
            id=BUDGET_ROW_ID,
            remaining_tokens=tok,
            remaining_usd=usd,
            updated_at=now,
        )
        .on_conflict_do_nothing(index_elements=["id"])
    )
    session.execute(stmt)
    session.flush()
    return get_budget(session) is not None


def debit_budget(
    session: Session,
    *,
    tokens: int,
    usd: Decimal,
) -> AnthropicPrepaidBudgetRow | None:
    """Atomically debit tokens and USD. Returns row if debited, else None (missing or insufficient)."""
    if tokens < 0 or usd < 0:
        raise ValueError("debit_amounts_must_be_non_negative")
    if tokens == 0 and usd == 0:
        return get_budget(session)
    if not seed_from_env_if_missing(session):
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
    session.flush()
    return session.get(AnthropicPrepaidBudgetRow, BUDGET_ROW_ID)
