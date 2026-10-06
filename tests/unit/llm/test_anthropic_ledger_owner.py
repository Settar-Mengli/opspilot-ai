"""F1: AnthropicProvider + BudgetAwareGateway + recorder — single ledger/row owner."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from opspilot.llm.errors import LlmProvidersExhausted
from opspilot.llm.gateway import session_attempt_recorder
from opspilot.llm.operator_auth import OperatorAnthropicAuth
from opspilot.llm.providers.anthropic import AnthropicProvider
from opspilot.llm.routed import BudgetAwareGateway
from opspilot.llm.types import Message
from opspilot.persistence.models import LlmCallRow
from opspilot.persistence.repositories.anthropic_budget import get_budget, set_budget


@pytest.fixture()
def allow_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPSPILOT_FORCE_RULES", raising=False)
    monkeypatch.delenv("OPSPILOT_LLM_DISABLE", raising=False)
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_REQ_DAY", "100")
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_TOK_DAY", "100000")


def _enable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_ENABLED", "1")
    monkeypatch.setenv("OPSPILOT_DEMO_MODE", "0")
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_USD_PER_MTOK_IN", "1")
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_USD_PER_MTOK_OUT", "5")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")


def _auth() -> OperatorAnthropicAuth:
    return OperatorAnthropicAuth(role="demo_operator")


def _anthropic_count(session: Session) -> int:
    return int(
        session.scalar(select(func.count()).select_from(LlmCallRow).where(LlmCallRow.provider == "anthropic")) or 0
    )


@pytest.mark.usefixtures("allow_llm")
def test_e2e_success_one_row_ledger_matches_actual(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    _enable(monkeypatch)
    set_budget(db_session, tokens=100_000, usd=Decimal("10"))
    db_session.commit()
    before = get_budget(db_session)
    assert before is not None
    tok0 = int(before.remaining_tokens)
    usd0 = Decimal(before.remaining_usd)

    class _Usage:
        input_tokens = 100
        output_tokens = 50

    class _Block:
        type = "text"
        text = "ok"

    class _Resp:
        content = [_Block()]
        usage = _Usage()

    class _Messages:
        def create(self, **_k: Any) -> _Resp:
            return _Resp()

    class _Client:
        messages = _Messages()

    provider = AnthropicProvider(operator_auth=_auth(), session=db_session, client=_Client())
    gw = BudgetAwareGateway(
        [provider],
        session=db_session,
        recorder=session_attempt_recorder(db_session),
        observe=False,
    )
    result = gw.complete(task="ask", messages=[Message(role="user", content="hi")], max_tokens=32)
    assert result.text == "ok"
    db_session.expire_all()
    after = get_budget(db_session)
    assert after is not None
    actual_tokens = 150
    actual_usd = (Decimal(100) * 1 + Decimal(50) * 5) / Decimal(1_000_000)
    assert tok0 - after.remaining_tokens == actual_tokens
    assert usd0 - after.remaining_usd == actual_usd
    assert _anthropic_count(db_session) == 1
    row = db_session.scalars(select(LlmCallRow).where(LlmCallRow.provider == "anthropic")).one()
    assert row.status == "success"
    assert row.meta.get("reconciled") is True


@pytest.mark.usefixtures("allow_llm")
def test_e2e_4xx_ledger_unchanged_one_row(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    _enable(monkeypatch)
    set_budget(db_session, tokens=100_000, usd=Decimal("10"))
    db_session.commit()
    before = get_budget(db_session)
    assert before is not None
    tok0 = int(before.remaining_tokens)
    usd0 = Decimal(before.remaining_usd)

    class _Exc(Exception):
        status_code = 400

    class _Messages:
        def create(self, **_k: Any) -> Any:
            raise _Exc("bad")

    class _Client:
        messages = _Messages()

    provider = AnthropicProvider(operator_auth=_auth(), session=db_session, client=_Client())
    gw = BudgetAwareGateway(
        [provider],
        session=db_session,
        recorder=session_attempt_recorder(db_session),
        observe=False,
    )
    with pytest.raises(LlmProvidersExhausted):
        gw.complete(task="ask", messages=[Message(role="user", content="hi")], max_tokens=16)
    db_session.expire_all()
    after = get_budget(db_session)
    assert after is not None
    assert after.remaining_tokens == tok0
    assert after.remaining_usd == usd0
    assert _anthropic_count(db_session) == 1


@pytest.mark.usefixtures("allow_llm")
def test_e2e_timeout_keeps_reservation_one_row(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    _enable(monkeypatch)
    set_budget(db_session, tokens=100_000, usd=Decimal("10"))
    db_session.commit()
    before = get_budget(db_session)
    assert before is not None
    tok0 = int(before.remaining_tokens)

    class APITimeoutError(Exception):
        pass

    class _Messages:
        def create(self, **_k: Any) -> Any:
            raise APITimeoutError("timed out")

    class _Client:
        messages = _Messages()

    provider = AnthropicProvider(operator_auth=_auth(), session=db_session, client=_Client())
    gw = BudgetAwareGateway(
        [provider],
        session=db_session,
        recorder=session_attempt_recorder(db_session),
        observe=False,
    )
    with pytest.raises(LlmProvidersExhausted):
        gw.complete(task="ask", messages=[Message(role="user", content="hi")], max_tokens=16)
    db_session.expire_all()
    after = get_budget(db_session)
    assert after is not None
    assert after.remaining_tokens < tok0  # reservation kept
    assert _anthropic_count(db_session) == 1
    row = db_session.scalars(select(LlmCallRow).where(LlmCallRow.provider == "anthropic")).one()
    assert row.status == "timeout"
    assert row.meta.get("reconciled") is True


def test_pin_retired_env_and_debit_absent_from_src() -> None:
    root = Path("src")
    forbidden = (
        "OPSPILOT_ANTHROPIC_BUDGET_TOKENS",
        "OPSPILOT_ANTHROPIC_BUDGET_USD",
        "seed_from_env_if_missing",
        "_env_seed_amounts",
        "debit_budget",
    )
    hits: list[str] = []
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for needle in forbidden:
            if needle in text:
                hits.append(f"{path.as_posix()}:{needle}")
    assert hits == [], hits
