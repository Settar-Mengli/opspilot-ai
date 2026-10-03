"""Anthropic prepaid ledger (F-05 / D-023 plumbing)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from opspilot.persistence.repositories.anthropic_budget import (
    debit_budget,
    get_budget,
    seed_from_env_if_missing,
)


def test_seed_from_env_once(monkeypatch: pytest.MonkeyPatch, db_session: Session) -> None:
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_BUDGET_TOKENS", "1000")
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_BUDGET_USD", "2.5")
    assert seed_from_env_if_missing(db_session) is True
    row = get_budget(db_session)
    assert row is not None
    assert row.remaining_tokens == 1000
    assert row.remaining_usd == Decimal("2.5")

    monkeypatch.setenv("OPSPILOT_ANTHROPIC_BUDGET_TOKENS", "99999")
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_BUDGET_USD", "99")
    assert seed_from_env_if_missing(db_session) is True
    row2 = get_budget(db_session)
    assert row2 is not None
    assert row2.remaining_tokens == 1000
    assert row2.remaining_usd == Decimal("2.5")


def test_debit_success(monkeypatch: pytest.MonkeyPatch, db_session: Session) -> None:
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_BUDGET_TOKENS", "500")
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_BUDGET_USD", "1")
    updated = debit_budget(db_session, tokens=100, usd=Decimal("0.25"))
    assert updated is not None
    assert updated.remaining_tokens == 400
    assert updated.remaining_usd == Decimal("0.75")


def test_debit_fails_insufficient(monkeypatch: pytest.MonkeyPatch, db_session: Session) -> None:
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_BUDGET_TOKENS", "50")
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_BUDGET_USD", "0.10")
    assert debit_budget(db_session, tokens=100, usd=Decimal("0.01")) is None
    row = get_budget(db_session)
    assert row is not None
    assert row.remaining_tokens == 50
    assert row.remaining_usd == Decimal("0.10")
