"""Hermetic tests for OpenRouter :free enforcement (F-06)."""

from __future__ import annotations

import pytest

from opspilot.llm.providers.openai_compatible import (
    OpenAICompatibleProvider,
    openrouter_model_denied,
)
from opspilot.llm.types import AttemptStatus, Message


def test_openrouter_model_denied_non_free() -> None:
    assert openrouter_model_denied("some/model") == "openrouter_paid_model_denied"
    assert openrouter_model_denied("nvidia/nemotron-3-super-120b-a12b:free") is None


def test_openrouter_paid_allow_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_OPENROUTER_ALLOW_PAID", "1")
    assert openrouter_model_denied("some/paid-model") is None


def test_openrouter_complete_rejects_non_free(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPSPILOT_OPENROUTER_ALLOW_PAID", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "openai/gpt-4o")
    provider = OpenAICompatibleProvider("openrouter")
    result = provider.complete(
        task="ask",
        messages=[Message(role="user", content="hi")],
        max_tokens=10,
    )
    assert result.status is AttemptStatus.ERROR
    assert result.error_code == "openrouter_paid_model_denied"


def test_openrouter_complete_allows_free_suffix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPSPILOT_OPENROUTER_ALLOW_PAID", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "nvidia/nemotron-3-super-120b-a12b:free")

    class _Resp:
        status_code = 200
        text = "{}"
        headers: dict[str, str] = {}

        def json(self) -> dict:
            return {"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}], "usage": {}}

    provider = OpenAICompatibleProvider("openrouter")
    monkeypatch.setattr(provider._client, "post", lambda *a, **k: _Resp())
    result = provider.complete(
        task="ask",
        messages=[Message(role="user", content="hi")],
        max_tokens=10,
    )
    assert result.status is AttemptStatus.SUCCESS
    assert result.text == "ok"
