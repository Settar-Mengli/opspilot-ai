"""TQ-03: budget env parsing edges."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from opspilot.llm.budgets import _parse_cap, req_cap, try_consume_request


def test_parse_cap_invalid_empty() -> None:
    assert _parse_cap(None) is None
    assert _parse_cap("") is None
    assert _parse_cap("   ") is None
    assert _parse_cap("abc") is None
    assert _parse_cap("12") == 12


def test_parse_cap_zero_and_negative() -> None:
    assert _parse_cap("0") == 0
    assert _parse_cap("-5") == -5


def test_req_cap_le_zero_denies(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_REQ_DAY", "0")
    assert req_cap("gemini") == 0
    assert try_consume_request(db_session, provider="gemini") is False
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_REQ_DAY", "-1")
    assert try_consume_request(db_session, provider="gemini") is False
