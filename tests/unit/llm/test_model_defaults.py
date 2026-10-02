"""C11-approved model defaults when *_MODEL env is unset."""

from __future__ import annotations

import pytest

from opspilot.config.settings import AISettings
from opspilot.llm.capabilities import JsonMode, json_mode_for
from opspilot.llm.model_defaults import (
    CLOUDFLARE_DEFAULT_MODEL,
    DEFAULT_MODELS,
    GEMINI_ASK_DEFAULT_MODEL,
    GEMINI_DEFAULT_MODEL,
    GROQ_DEFAULT_MODEL,
    MISTRAL_DEFAULT_MODEL,
    OPENROUTER_DEFAULT_MODEL,
)
from opspilot.llm.providers.gemini import resolve_gemini_model
from opspilot.llm.providers.openai_compatible import config_for, resolve_task_model


@pytest.fixture()
def clear_model_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "GEMINI_MODEL",
        "GROQ_MODEL",
        "MISTRAL_MODEL",
        "OPENROUTER_MODEL",
        "CLOUDFLARE_MODEL",
        "OLLAMA_MODEL",
        "GEMINI_MODEL_ASK",
        "GROQ_MODEL_ASK",
        "MISTRAL_MODEL_ASK",
        "OPENROUTER_MODEL_ASK",
        "CLOUDFLARE_MODEL_ASK",
    ):
        monkeypatch.delenv(name, raising=False)


def test_approved_defaults_match_c11(clear_model_env: None) -> None:
    assert DEFAULT_MODELS["gemini"] == "gemini-3.5-flash-lite"
    assert GEMINI_ASK_DEFAULT_MODEL == "gemini-3.8-flash"
    assert DEFAULT_MODELS["groq"] == "openai/gpt-oss-20b"
    assert DEFAULT_MODELS["mistral"] == "ministral-3b-2512"
    assert DEFAULT_MODELS["openrouter"] == "nvidia/nemotron-3-super-120b-a12b:free"
    assert DEFAULT_MODELS["cloudflare"] == "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
    assert OPENROUTER_DEFAULT_MODEL.endswith(":free")


def test_gemini_ask_default_independent_of_shared_model(clear_model_env: None) -> None:
    assert resolve_gemini_model("ask") == GEMINI_ASK_DEFAULT_MODEL
    assert resolve_gemini_model("triage") == GEMINI_DEFAULT_MODEL
    assert resolve_gemini_model("evening") == GEMINI_DEFAULT_MODEL
    assert resolve_gemini_model("insights") == GEMINI_DEFAULT_MODEL


def test_gemini_model_ask_override_only_affects_ask(clear_model_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    monkeypatch.setenv("GEMINI_MODEL_ASK", "gemini-ask-override-test")
    assert resolve_gemini_model("ask") == "gemini-ask-override-test"
    assert resolve_gemini_model("triage") == "gemini-3.5-flash-lite"
    assert resolve_gemini_model("evening") == "gemini-3.5-flash-lite"
    assert resolve_gemini_model("insights") == "gemini-3.5-flash-lite"


def test_gemini_ask_ignores_shared_model_when_ask_unset(clear_model_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    assert resolve_gemini_model("ask") == GEMINI_ASK_DEFAULT_MODEL
    assert resolve_gemini_model("triage") == "gemini-3.5-flash-lite"


def test_openai_compat_resolves_approved_defaults_when_unset(
    clear_model_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "acct")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "tok")
    cases = [
        ("groq", GROQ_DEFAULT_MODEL),
        ("mistral", MISTRAL_DEFAULT_MODEL),
        ("openrouter", OPENROUTER_DEFAULT_MODEL),
        ("cloudflare", CLOUDFLARE_DEFAULT_MODEL),
    ]
    for provider, expected in cases:
        cfg = config_for(provider)
        resolved = resolve_task_model(provider, "ask", None, cfg.model_env, cfg.default_model)
        assert resolved == expected, provider
        assert cfg.default_model == expected


def test_openrouter_default_ends_with_free(clear_model_env: None) -> None:
    cfg = config_for("openrouter")
    assert cfg.default_model.endswith(":free")
    assert "openrouter/auto" not in cfg.default_model


def test_groq_default_uses_native_schema_strict(clear_model_env: None) -> None:
    assert json_mode_for("groq", GROQ_DEFAULT_MODEL) is JsonMode.NATIVE_SCHEMA


def test_aisettings_uses_approved_defaults_when_unset(clear_model_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("INFERENCE_PROVIDER_ORDER", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    settings = AISettings()
    assert settings.provider == "gemini"
    assert settings.model == GEMINI_DEFAULT_MODEL
