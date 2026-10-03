"""Anthropic prepaid budget ledger (D-023 / B6 plumbing)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from opspilot.persistence.models import AnthropicPrepaidBudgetRow

BUDGET_ROW_ID = 1


def get_budget(session: Session) -> AnthropicPrepaidBudgetRow | None:
    return session.get(AnthropicPrepaidBudgetRow, BUDGET_ROW_ID)


def upsert_budget(
    session: Session,
    *,
    remaining_tokens: int,
    remaining_usd: Decimal,
) -> AnthropicPrepaidBudgetRow:
    now = datetime.now(UTC)
    stmt = pg_insert(AnthropicPrepaidBudgetRow).values(
        id=BUDGET_ROW_ID,
        remaining_tokens=remaining_tokens,
        remaining_usd=remaining_usd,
        updated_at=now,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={
            "remaining_tokens": stmt.excluded.remaining_tokens,
            "remaining_usd": stmt.excluded.remaining_usd,
            "updated_at": stmt.excluded.updated_at,
        },
    )
    session.execute(stmt)
    session.flush()
    row = session.get(AnthropicPrepaidBudgetRow, BUDGET_ROW_ID)
    assert row is not None
    return row


def debit_budget(
    session: Session,
    *,
    tokens: int,
    usd: Decimal,
) -> AnthropicPrepaidBudgetRow | None:
    """Atomically debit tokens and USD. Returns row if debited, else None (missing or insufficient)."""
    if tokens < 0 or usd < 0:
        raise ValueError("debit_amounts_must_be_non_negative")
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
        .returning(AnthropicPrepaidBudgetRow.id)
    )
    if result.scalar_one_or_none() is None:
        session.flush()
        return None
    session.flush()
    return session.get(AnthropicPrepaidBudgetRow, BUDGET_ROW_ID)
