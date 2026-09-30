"""D-023 Anthropic gate tests — never construct client when gated off."""

from __future__ import annotations

import pytest

from opspilot.llm.providers.anthropic import AnthropicProvider, gate_reason
from opspilot.llm.types import AttemptStatus, Message


def test_disabled_never_constructs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_ENABLED", "false")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    constructed: list[bool] = []

    def _track(*_a, **_k):  # type: ignore[no-untyped-def]
        constructed.append(True)
        raise AssertionError("must not construct")

    monkeypatch.setattr("anthropic.Anthropic", _track)
    provider = AnthropicProvider()
    result = provider.complete(
        task="demo_quality",
        messages=[Message(role="user", content="hi")],
        max_tokens=16,
    )
    assert result.status is AttemptStatus.POLICY_DENIED
    assert result.error_code == "anthropic_disabled"
    assert constructed == []
    assert gate_reason("demo_quality") == "anthropic_disabled"


def test_budget_zero_never_constructs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_ENABLED", "1")
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_BUDGET_TOKENS", "0")
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_BUDGET_USD", "5")
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_USD_PER_MTOK_IN", "0.25")
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_USD_PER_MTOK_OUT", "1.25")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    constructed: list[bool] = []

    def _track(*_a, **_k):  # type: ignore[no-untyped-def]
        constructed.append(True)
        raise AssertionError("must not construct")

    monkeypatch.setattr("anthropic.Anthropic", _track)
    result = AnthropicProvider().complete(
        task="leaderboard",
        messages=[Message(role="user", content="hi")],
        max_tokens=16,
    )
    assert result.status is AttemptStatus.BUDGET_DENIED
    assert constructed == []


def test_missing_usd_rates_never_constructs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_ENABLED", "1")
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_BUDGET_TOKENS", "10000")
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_BUDGET_USD", "5")
    monkeypatch.delenv("OPSPILOT_ANTHROPIC_USD_PER_MTOK_IN", raising=False)
    monkeypatch.delenv("OPSPILOT_ANTHROPIC_USD_PER_MTOK_OUT", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    constructed: list[bool] = []

    def _track(*_a, **_k):  # type: ignore[no-untyped-def]
        constructed.append(True)
        raise AssertionError("must not construct")

    monkeypatch.setattr("anthropic.Anthropic", _track)
    result = AnthropicProvider().complete(
        task="judge_calibration",
        messages=[Message(role="user", content="hi")],
        max_tokens=16,
    )
    assert result.status is AttemptStatus.POLICY_DENIED
    assert result.error_code == "missing_usd_rates"
    assert constructed == []


def test_ask_never_allowlisted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_ENABLED", "1")
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_BUDGET_TOKENS", "10000")
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_BUDGET_USD", "5")
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_USD_PER_MTOK_IN", "0.25")
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_USD_PER_MTOK_OUT", "1.25")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    constructed: list[bool] = []

    def _track(*_a, **_k):  # type: ignore[no-untyped-def]
        constructed.append(True)
        raise AssertionError("must not construct")

    monkeypatch.setattr("anthropic.Anthropic", _track)
    result = AnthropicProvider().complete(
        task="ask",
        messages=[Message(role="user", content="hi")],
        max_tokens=16,
    )
    assert result.status is AttemptStatus.POLICY_DENIED
    assert result.error_code == "task_not_allowlisted"
    assert constructed == []


def test_enabled_allowlisted_constructs_with_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_ENABLED", "1")
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_BUDGET_TOKENS", "10000")
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_BUDGET_USD", "5")
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_USD_PER_MTOK_IN", "0.25")
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_USD_PER_MTOK_OUT", "1.25")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    class _Usage:
        input_tokens = 10
        output_tokens = 5

    class _Block:
        type = "text"
        text = "ok"

    class _Resp:
        content = [_Block()]
        usage = _Usage()

    class _Messages:
        def create(self, **_kwargs):  # type: ignore[no-untyped-def]
            return _Resp()

    class _Client:
        messages = _Messages()

    constructed: list[bool] = []

    def _track(*_a, **_k):  # type: ignore[no-untyped-def]
        constructed.append(True)
        return _Client()

    monkeypatch.setattr("anthropic.Anthropic", _track)
    # Bypass autouse Anthropic forbid by patching after conftest — use injected client instead.
    provider = AnthropicProvider(client=_Client())
    result = provider.complete(
        task="demo_quality",
        messages=[Message(role="user", content="hi")],
        max_tokens=16,
    )
    assert result.status is AttemptStatus.SUCCESS
    assert result.text == "ok"
    assert constructed == []  # injected client — no Anthropic() call
