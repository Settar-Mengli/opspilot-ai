"""AISettings resolves free-tier env only; OPSPILOT_AI_* is ignored."""

from __future__ import annotations

import pytest

from opspilot.config.settings import AISettings


def test_ignores_retired_opspilot_ai_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_AI_PROVIDER", "anthropic")
    monkeypatch.setenv("OPSPILOT_AI_MODEL", "should-never-appear")
    monkeypatch.setenv("OPSPILOT_AI_API_KEY", "legacy-key-must-be-ignored")
    monkeypatch.delenv("INFERENCE_PROVIDER_ORDER", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

    settings = AISettings()
    assert settings.provider == "gemini"
    assert settings.model == "gemini-3.5-flash-lite"
    assert settings.api_key is None
    assert settings.api_key != "legacy-key-must-be-ignored"
    assert settings.model != "should-never-appear"


def test_first_configured_provider_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INFERENCE_PROVIDER_ORDER", "gemini,groq")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test-only")
    monkeypatch.setenv("GROQ_MODEL", "openai/gpt-oss-20b")
    monkeypatch.setenv("OPSPILOT_AI_PROVIDER", "mistral")
    monkeypatch.setenv("OPSPILOT_AI_API_KEY", "ignored")

    settings = AISettings()
    assert settings.provider == "groq"
    assert settings.model == "openai/gpt-oss-20b"
    assert settings.api_key == "gsk-test-only"
