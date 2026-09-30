"""Hermetic factory and network-block proofs."""

from __future__ import annotations

import pytest

from opspilot.adapters.factory import get_adapter
from opspilot.adapters.rule_based import RuleBasedAdapter


def test_force_rules_returns_rule_based_even_with_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPSPILOT_FORCE_RULES", "1")
    monkeypatch.delenv("OPSPILOT_LLM_DISABLE", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-fake")

    constructed: list[bool] = []

    def _track(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        constructed.append(True)
        raise AssertionError("Anthropic client must not be constructed")

    monkeypatch.setattr("anthropic.Anthropic", _track)

    adapter = get_adapter()
    assert isinstance(adapter, RuleBasedAdapter)
    assert constructed == []


def test_llm_disable_returns_rule_based_without_force_rules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPSPILOT_FORCE_RULES", raising=False)
    monkeypatch.setenv("OPSPILOT_LLM_DISABLE", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-fake")

    constructed: list[bool] = []

    def _track(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        constructed.append(True)
        raise AssertionError("Anthropic client must not be constructed")

    monkeypatch.setattr("anthropic.Anthropic", _track)

    adapter = get_adapter()
    assert isinstance(adapter, RuleBasedAdapter)
    assert constructed == []


def test_force_rules_uses_rule_adapter_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPSPILOT_FORCE_RULES", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-fake")

    import builtins

    real_import = builtins.__import__
    banned = {
        "opspilot.adapters.claude_adapter",
        "opspilot.adapters.conversation_adapter",
        "opspilot.adapters.evening_adapter",
        "opspilot.adapters.insights_adapter",
        "opspilot.domain.models",
    }

    def _guarded_import(name, *args, **kwargs):  # type: ignore[no-untyped-def]
        if name in banned:
            raise AssertionError(f"{name} must not be imported under FORCE_RULES")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _guarded_import)
    adapter = get_adapter()
    assert isinstance(adapter, RuleBasedAdapter)


def test_public_network_is_blocked_by_pytest_socket() -> None:
    import urllib.request

    from pytest_socket import SocketBlockedError, SocketConnectBlockedError

    with pytest.raises((SocketBlockedError, SocketConnectBlockedError)):
        urllib.request.urlopen("https://example.com", timeout=2)
