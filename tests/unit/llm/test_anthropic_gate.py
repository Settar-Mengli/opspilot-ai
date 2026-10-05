"""D-023 Anthropic gate tests — operator auth + ledger; never live HTTP."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy.orm import Session

from opspilot.llm.operator_auth import OperatorAnthropicAuth
from opspilot.llm.providers.anthropic import AnthropicProvider, gate_reason
from opspilot.llm.types import AttemptStatus, Message
from opspilot.persistence.models import LlmCallRow
from opspilot.persistence.repositories.anthropic_budget import (
    ANTHROPIC_EST_INPUT_CAP,
    get_budget,
    reconcile_reservation,
    set_budget,
)


def _auth() -> OperatorAnthropicAuth:
    return OperatorAnthropicAuth(role="demo_operator")


def _enable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_ENABLED", "1")
    monkeypatch.setenv("OPSPILOT_DEMO_MODE", "0")
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_USD_PER_MTOK_IN", "1")
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_USD_PER_MTOK_OUT", "5")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")


def test_no_auth_never_constructs(monkeypatch: pytest.MonkeyPatch) -> None:
    _enable(monkeypatch)
    constructed: list[bool] = []

    def _track(*_a: Any, **_k: Any) -> None:
        constructed.append(True)
        raise AssertionError("must not construct")

    monkeypatch.setattr("anthropic.Anthropic", _track)
    result = AnthropicProvider().complete(
        task="ask",
        messages=[Message(role="user", content="hi")],
        max_tokens=16,
    )
    assert result.status is AttemptStatus.POLICY_DENIED
    assert result.error_code == "operator_auth_required"
    assert constructed == []


def test_ask_allowlisted_under_auth(monkeypatch: pytest.MonkeyPatch, db_session: Session) -> None:
    _enable(monkeypatch)
    set_budget(db_session, tokens=100000, usd=Decimal("10"))
    db_session.commit()
    assert gate_reason("ask", operator_auth=_auth(), session=db_session, est_input=256) is None


def test_legacy_task_not_allowlisted(monkeypatch: pytest.MonkeyPatch) -> None:
    _enable(monkeypatch)
    assert (
        gate_reason("demo_quality", operator_auth=_auth(), est_input=256)  # type: ignore[arg-type]
        == "task_not_allowlisted"
    )


def test_missing_usd_rates_never_constructs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_ENABLED", "1")
    monkeypatch.setenv("OPSPILOT_DEMO_MODE", "0")
    monkeypatch.delenv("OPSPILOT_ANTHROPIC_USD_PER_MTOK_IN", raising=False)
    monkeypatch.delenv("OPSPILOT_ANTHROPIC_USD_PER_MTOK_OUT", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    constructed: list[bool] = []
    monkeypatch.setattr("anthropic.Anthropic", lambda **_k: constructed.append(True))
    result = AnthropicProvider(operator_auth=_auth()).complete(
        task="ask",
        messages=[Message(role="user", content="hi")],
        max_tokens=16,
    )
    assert result.status is AttemptStatus.POLICY_DENIED
    assert result.error_code == "missing_usd_rates"
    assert constructed == []


def test_est_input_over_cap_skips(monkeypatch: pytest.MonkeyPatch, db_session: Session) -> None:
    _enable(monkeypatch)
    set_budget(db_session, tokens=100000, usd=Decimal("10"))
    db_session.commit()
    assert (
        gate_reason(
            "ask",
            operator_auth=_auth(),
            session=db_session,
            est_input=ANTHROPIC_EST_INPUT_CAP + 1,
        )
        == "est_input_over_cap"
    )


def test_client_before_reserve_missing_key(monkeypatch: pytest.MonkeyPatch, db_session: Session) -> None:
    _enable(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    set_budget(db_session, tokens=100000, usd=Decimal("10"))
    db_session.commit()
    before = get_budget(db_session)
    assert before is not None
    tok_before = before.remaining_tokens
    result = AnthropicProvider(operator_auth=_auth(), session=db_session, api_key="").complete(
        task="ask",
        messages=[Message(role="user", content="hi")],
        max_tokens=16,
    )
    assert result.error_code == "missing_api_key"
    after = get_budget(db_session)
    assert after is not None
    assert after.remaining_tokens == tok_before


def test_anthropic_messages_create_kwargs_no_temperature(monkeypatch: pytest.MonkeyPatch, db_session: Session) -> None:
    _enable(monkeypatch)
    set_budget(db_session, tokens=100000, usd=Decimal("10"))
    db_session.commit()

    class _Usage:
        input_tokens = 10
        output_tokens = 5

    class _Block:
        type = "text"
        text = '{"ok":true}'

    class _Resp:
        content = [_Block()]
        usage = _Usage()

    class _Messages:
        def __init__(self) -> None:
            self.kwargs: dict[str, Any] | None = None

        def create(self, **kwargs: Any) -> _Resp:
            self.kwargs = kwargs
            return _Resp()

    class _Client:
        def __init__(self) -> None:
            self.messages = _Messages()

    client = _Client()
    provider = AnthropicProvider(operator_auth=_auth(), session=db_session, client=client)
    result = provider.complete(
        task="ask",
        messages=[Message(role="user", content="hi")],
        max_tokens=32,
    )
    assert result.status is AttemptStatus.SUCCESS
    assert client.messages.kwargs is not None
    assert "temperature" not in client.messages.kwargs

    captured: dict[str, Any] = {}

    def _ctor(**kwargs: Any) -> _Client:
        captured.update(kwargs)
        return _Client()

    import anthropic as anthropic_mod

    monkeypatch.setattr(anthropic_mod, "Anthropic", _ctor)
    p2 = AnthropicProvider(operator_auth=_auth(), session=db_session, api_key="sk-ant-test")
    p2.complete(task="ask", messages=[Message(role="user", content="hi")], max_tokens=8)
    assert captured.get("max_retries") == 0
    assert "timeout" in captured
    assert "temperature" not in (p2._last_create_kwargs or {})


def test_4xx_full_refund(monkeypatch: pytest.MonkeyPatch, db_session: Session) -> None:
    _enable(monkeypatch)
    set_budget(db_session, tokens=1000, usd=Decimal("1"))
    db_session.commit()

    class _Exc(Exception):
        status_code = 400

    class _Messages:
        def create(self, **_k: Any) -> Any:
            raise _Exc("bad request")

    class _Client:
        messages = _Messages()

    provider = AnthropicProvider(operator_auth=_auth(), session=db_session, client=_Client())
    result = provider.complete(task="ask", messages=[Message(role="user", content="hi")], max_tokens=16)
    assert result.status is AttemptStatus.ERROR
    row = get_budget(db_session)
    assert row is not None
    assert row.remaining_tokens == 1000
    assert row.remaining_usd == Decimal("1")


def test_pre_send_full_refund(monkeypatch: pytest.MonkeyPatch, db_session: Session) -> None:
    """TypeError before HTTP is treated as refund via status_code-less path → keep by default.

    Explicit pre-send: raise ValueError with no status → keep per fail-closed.
    For full refund of true pre-send, use http-less Authentication-style with marker.
    """
    _enable(monkeypatch)
    set_budget(db_session, tokens=1000, usd=Decimal("1"))
    db_session.commit()

    class _AuthExc(Exception):
        status_code = 401

    class _Messages:
        def create(self, **_k: Any) -> Any:
            raise _AuthExc("unauthorized")

    class _Client:
        messages = _Messages()

    provider = AnthropicProvider(operator_auth=_auth(), session=db_session, client=_Client())
    provider.complete(task="ask", messages=[Message(role="user", content="hi")], max_tokens=16)
    row = get_budget(db_session)
    assert row is not None
    assert row.remaining_tokens == 1000


def test_5xx_keep_reservation(monkeypatch: pytest.MonkeyPatch, db_session: Session) -> None:
    _enable(monkeypatch)
    set_budget(db_session, tokens=1000, usd=Decimal("1"))
    db_session.commit()

    class _Exc(Exception):
        status_code = 503

    class _Messages:
        def create(self, **_k: Any) -> Any:
            raise _Exc("unavailable")

    class _Client:
        messages = _Messages()

    provider = AnthropicProvider(operator_auth=_auth(), session=db_session, client=_Client())
    provider.complete(task="ask", messages=[Message(role="user", content="hi")], max_tokens=16)
    row = get_budget(db_session)
    assert row is not None
    assert row.remaining_tokens < 1000


def test_reservation_kept_on_timeout(monkeypatch: pytest.MonkeyPatch, db_session: Session) -> None:
    _enable(monkeypatch)
    set_budget(db_session, tokens=1000, usd=Decimal("1"))
    db_session.commit()

    class APITimeoutError(Exception):
        pass

    class _Messages:
        def create(self, **_k: Any) -> Any:
            raise APITimeoutError("timed out")

    class _Client:
        messages = _Messages()

    provider = AnthropicProvider(operator_auth=_auth(), session=db_session, client=_Client())
    result = provider.complete(task="ask", messages=[Message(role="user", content="hi")], max_tokens=16)
    assert result.status is AttemptStatus.TIMEOUT
    row = get_budget(db_session)
    assert row is not None
    assert row.remaining_tokens < 1000


def test_reconcile_idempotent_after_step_timeout_late_result(db_session: Session) -> None:
    from opspilot.persistence.repositories.anthropic_budget import reserve_and_open_call

    set_budget(db_session, tokens=500, usd=Decimal("1"))
    db_session.commit()
    call = reserve_and_open_call(db_session, tokens=100, usd=Decimal("0.25"), task="ask", model="m")
    db_session.commit()
    assert call is not None
    assert reconcile_reservation(
        db_session,
        call_id=call.id,
        final_status="timeout",
        ledger_op="keep",
        error_code="timeout",
    )
    db_session.commit()
    mid = get_budget(db_session)
    assert mid is not None
    tokens_mid = mid.remaining_tokens
    # Late success would try refund_delta — must no-op
    assert (
        reconcile_reservation(
            db_session,
            call_id=call.id,
            final_status="success",
            ledger_op="refund_delta",
            actual_tokens=10,
            actual_usd=Decimal("0.01"),
        )
        is False
    )
    db_session.commit()
    end = get_budget(db_session)
    assert end is not None
    assert end.remaining_tokens == tokens_mid
    row = db_session.get(LlmCallRow, call.id)
    assert row is not None
    assert row.status == "timeout"
