"""LlmCall persistence + gateway attempt recording."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from opspilot.llm import FakeProvider, LlmGateway, Message
from opspilot.llm.errors import LlmProvidersExhausted
from opspilot.llm.gateway import session_attempt_recorder
from opspilot.llm.prompts.versioning import prompt_version_sha256
from opspilot.llm.routed import BudgetAwareGateway
from opspilot.llm.types import AttemptStatus, ProviderResult
from opspilot.obs.tracing import LlmSpanAttrs, append_llm_jsonl
from opspilot.persistence.models import LlmCallRow
from opspilot.persistence.repositories.anthropic_budget import get_budget


@pytest.fixture()
def allow_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPSPILOT_FORCE_RULES", raising=False)
    monkeypatch.delenv("OPSPILOT_LLM_DISABLE", raising=False)


@pytest.mark.usefixtures("allow_llm")
def test_fake_complete_writes_llm_call_row(db_session: Session) -> None:
    gw = LlmGateway(
        [FakeProvider(text_responder=lambda _t, _m: "hello")],
        recorder=session_attempt_recorder(db_session),
        observe=False,
        request_id="req-test-1",
    )
    result = gw.complete(task="ask", messages=[Message(role="user", content="hi")])
    assert result.text == "hello"

    rows = list(db_session.scalars(select(LlmCallRow)).all())
    assert len(rows) == 1
    row = rows[0]
    assert row.task == "ask"
    assert row.provider == "fake"
    assert row.status == "success"
    assert row.request_id == "req-test-1"
    assert row.tokens_out >= 1


@pytest.mark.usefixtures("allow_llm")
def test_failover_writes_one_row_per_attempt(db_session: Session) -> None:
    failing = FakeProvider(
        name="bad",
        complete_results=[ProviderResult(status=AttemptStatus.ERROR, error_code="boom", model="bad-v1")],
    )
    ok = FakeProvider(name="good", text_responder=lambda _t, _m: "ok")
    gw = LlmGateway(
        [failing, ok],
        recorder=session_attempt_recorder(db_session),
        observe=False,
    )
    gw.complete(task="ask", messages=[Message(role="user", content="x")])
    rows = list(db_session.scalars(select(LlmCallRow).order_by(LlmCallRow.id)).all())
    assert [r.provider for r in rows] == ["bad", "good"]
    assert [r.status for r in rows] == ["error", "success"]


@pytest.mark.usefixtures("allow_llm")
def test_recorder_persists_usd_estimate_from_raw(db_session: Session) -> None:
    gw = LlmGateway(
        [
            FakeProvider(
                name="anthropic",
                complete_results=[
                    ProviderResult(
                        status=AttemptStatus.SUCCESS,
                        text="ok",
                        model="claude-test",
                        input_tokens=10,
                        output_tokens=5,
                        raw={"usd_estimate": "0.001234"},
                    )
                ],
            )
        ],
        recorder=session_attempt_recorder(db_session),
        observe=False,
    )
    gw.complete(task="demo_quality", messages=[Message(role="user", content="hi")])
    row = db_session.scalars(select(LlmCallRow)).one()
    assert row.usd_estimate == Decimal("0.001234")


@pytest.mark.usefixtures("allow_llm")
def test_recorder_skips_anthropic_when_ledger_row_owned(db_session: Session) -> None:
    """Reserve path owns the row: recorder must not debit or insert a second llm_calls row."""
    from opspilot.persistence.repositories.anthropic_budget import set_budget

    set_budget(db_session, tokens=1000, usd=Decimal("5"))
    db_session.commit()
    before_tokens = get_budget(db_session)
    assert before_tokens is not None
    tok0 = before_tokens.remaining_tokens
    gw = LlmGateway(
        [
            FakeProvider(
                name="anthropic",
                complete_results=[
                    ProviderResult(
                        status=AttemptStatus.SUCCESS,
                        text="ok",
                        model="claude-test",
                        input_tokens=100,
                        output_tokens=50,
                        raw={"usd_estimate": "0.5"},
                        meta={"ledger_row_owned": True},
                    )
                ],
            )
        ],
        recorder=session_attempt_recorder(db_session),
        observe=False,
    )
    gw.complete(task="ask", messages=[Message(role="user", content="hi")])
    budget = get_budget(db_session)
    assert budget is not None
    assert budget.remaining_tokens == tok0  # no debit
    assert list(db_session.scalars(select(LlmCallRow)).all()) == []  # no duplicate insert


@pytest.mark.usefixtures("allow_llm")
def test_recorder_records_anthropic_prereserve_denial_once(db_session: Session) -> None:
    """Pre-reserve denial (no ledger_row_owned) is still recorded once; no debit."""
    gw = LlmGateway(
        [
            FakeProvider(
                name="anthropic",
                complete_results=[
                    ProviderResult(
                        status=AttemptStatus.POLICY_DENIED,
                        model="claude-test",
                        error_code="operator_auth_required",
                    )
                ],
            )
        ],
        recorder=session_attempt_recorder(db_session),
        observe=False,
    )
    with pytest.raises(LlmProvidersExhausted):
        gw.complete(task="ask", messages=[Message(role="user", content="hi")])
    rows = list(db_session.scalars(select(LlmCallRow)).all())
    assert len(rows) == 1
    assert rows[0].provider == "anthropic"
    assert rows[0].status == "policy_denied"
    assert get_budget(db_session) is None


@pytest.mark.usefixtures("allow_llm")
def test_budget_gateway_writes_prompt_version_and_request_id(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_REQ_DAY", "5")
    monkeypatch.setenv("OPSPILOT_BUDGET_GEMINI_TOK_DAY", "5000")
    messages = [Message(role="user", content="hi")]
    expected_pv = prompt_version_sha256(task="ask", messages=messages)
    gw = BudgetAwareGateway(
        [FakeProvider(name="gemini", text_responder=lambda _t, _m: "pv")],
        session=db_session,
        recorder=session_attempt_recorder(db_session),
        observe=False,
        request_id="req-pv-1",
    )
    gw.complete(task="ask", messages=messages)
    row = db_session.scalars(select(LlmCallRow)).one()
    assert row.request_id == "req-pv-1"
    assert row.prompt_version == expected_pv


def test_append_llm_jsonl_writes_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setenv("OPSPILOT_LLM_JSONL", "1")
    path = append_llm_jsonl(
        LlmSpanAttrs(task="ask", provider="fake", model="fake-v1", status="success"),
        directory=tmp_path,
    )
    assert path is not None
    assert path.exists()
    assert "fake" in path.read_text(encoding="utf-8")
