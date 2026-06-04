import importlib

import pytest


MISSING_KEY_MESSAGE = (
    "I need an Anthropic API key to answer questions. "
    "Set ANTHROPIC_API_KEY in your environment and I'll be ready."
)
UNAVAILABLE_MESSAGE = (
    "I ran into an issue answering that. The API may be unavailable. "
    "Please try again in a moment."
)


def _reload_with_env(monkeypatch: pytest.MonkeyPatch, **env: str | None):
    for key in [
        "OPSPILOT_AI_PROVIDER",
        "OPSPILOT_AI_MODEL",
        "OPSPILOT_AI_API_KEY",
        "ANTHROPIC_API_KEY",
    ]:
        monkeypatch.delenv(key, raising=False)

    for key, value in env.items():
        if value is None:
            continue
        monkeypatch.setenv(key, value)

    import opspilot.config.settings as settings_module
    import opspilot.adapters.conversation_adapter as conversation_module

    settings_module = importlib.reload(settings_module)
    conversation_module = importlib.reload(conversation_module)
    return settings_module, conversation_module


def _stub_anthropic(conversation_module):
    captured: dict[str, object] = {}

    class _FakeMessages:
        def create(self, **kwargs):
            captured["create"] = kwargs
            text_block = type("TextBlock", (), {"text": " Stub answer "})()
            return type("Response", (), {"content": [text_block]})()

    class _FakeClient:
        def __init__(self, api_key: str):
            captured["api_key"] = api_key
            self.messages = _FakeMessages()

    conversation_module.Anthropic = _FakeClient
    return captured


def test_default_resolution_uses_anthropic_provider_and_default_model(monkeypatch: pytest.MonkeyPatch):
    settings_module, conversation_module = _reload_with_env(
        monkeypatch,
        ANTHROPIC_API_KEY="legacy-key",
    )
    captured = _stub_anthropic(conversation_module)

    answer = conversation_module.answer_question("What should I prioritize?")

    assert answer == "Stub answer"
    assert settings_module.ai_settings.provider == "anthropic"
    assert settings_module.ai_settings.model == "claude-haiku-4-5-20251001"
    assert captured["api_key"] == "legacy-key"
    assert captured["create"]["model"] == "claude-haiku-4-5-20251001"


def test_opspilot_ai_model_overrides_default_model(monkeypatch: pytest.MonkeyPatch):
    _, conversation_module = _reload_with_env(
        monkeypatch,
        ANTHROPIC_API_KEY="legacy-key",
        OPSPILOT_AI_MODEL="claude-3-5-haiku-latest",
    )
    captured = _stub_anthropic(conversation_module)

    answer = conversation_module.answer_question("Give me a quick summary")

    assert answer == "Stub answer"
    assert captured["create"]["model"] == "claude-3-5-haiku-latest"


def test_opspilot_api_key_takes_precedence_over_anthropic_api_key(monkeypatch: pytest.MonkeyPatch):
    _, conversation_module = _reload_with_env(
        monkeypatch,
        ANTHROPIC_API_KEY="legacy-key",
        OPSPILOT_AI_API_KEY="primary-key",
    )
    captured = _stub_anthropic(conversation_module)

    answer = conversation_module.answer_question("What changed?")

    assert answer == "Stub answer"
    assert captured["api_key"] == "primary-key"


def test_missing_key_returns_existing_fallback_message(monkeypatch: pytest.MonkeyPatch):
    _, conversation_module = _reload_with_env(monkeypatch)

    answer = conversation_module.answer_question("Any updates?")

    assert answer == MISSING_KEY_MESSAGE


def test_unsupported_provider_fails_safely(monkeypatch: pytest.MonkeyPatch):
    _, conversation_module = _reload_with_env(
        monkeypatch,
        OPSPILOT_AI_PROVIDER="openai",
        OPSPILOT_AI_API_KEY="some-key",
    )

    answer = conversation_module.answer_question("Any updates?")

    assert answer == UNAVAILABLE_MESSAGE
