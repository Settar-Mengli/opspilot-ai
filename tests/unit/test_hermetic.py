"""Hermetic factory and network-block proofs."""

from __future__ import annotations

import pytest

from opspilot.adapters.factory import get_adapter
from opspilot.adapters.rule_based import RuleBasedAdapter


def test_force_rules_returns_rule_based_even_with_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPSPILOT_FORCE_RULES", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-fake")

    constructed: list[bool] = []

    def _track(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        constructed.append(True)
        raise AssertionError("Anthropic client must not be constructed")

    monkeypatch.setattr("anthropic.Anthropic", _track)

    adapter = get_adapter()
    assert isinstance(adapter, RuleBasedAdapter)
    assert constructed == []


def test_force_rules_does_not_import_claude_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPSPILOT_FORCE_RULES", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-fake")

    import builtins

    real_import = builtins.__import__

    def _guarded_import(name, *args, **kwargs):  # type: ignore[no-untyped-def]
        if name == "opspilot.adapters.claude_adapter" or name.endswith(
            "claude_adapter"
        ):
            raise AssertionError("claude_adapter must not be imported under FORCE_RULES")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _guarded_import)
    adapter = get_adapter()
    assert isinstance(adapter, RuleBasedAdapter)


def test_public_network_is_blocked_by_pytest_socket() -> None:
    import urllib.request

    with pytest.raises(Exception):
        urllib.request.urlopen("https://example.com", timeout=2)
