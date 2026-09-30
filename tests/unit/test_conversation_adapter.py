"""Ask service / conversation wrapper tests (gateway path)."""

from __future__ import annotations

import pytest

from opspilot.llm.types import CompletionResult
from opspilot.services import ask as ask_service

UNAVAILABLE_MESSAGE = "I ran into an issue answering that. The API may be unavailable. Please try again in a moment."
NO_PROVIDER_MESSAGE = (
    "I need a free-tier LLM key to answer questions. "
    "Set GEMINI_API_KEY or GROQ_API_KEY (see .env.example) and I'll be ready."
)


def test_empty_question() -> None:
    assert "didn't catch" in ask_service.answer_question("   ").lower()


def test_force_rules_soft(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_FORCE_RULES", "1")
    assert ask_service.answer_question("What needs attention?") == UNAVAILABLE_MESSAGE


def test_no_providers_soft(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPSPILOT_FORCE_RULES", raising=False)
    monkeypatch.delenv("OPSPILOT_LLM_DISABLE", raising=False)
    for key in (
        "GEMINI_API_KEY",
        "GROQ_API_KEY",
        "MISTRAL_API_KEY",
        "OPENROUTER_API_KEY",
        "CLOUDFLARE_API_TOKEN",
        "CLOUDFLARE_ACCOUNT_ID",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("INFERENCE_PROVIDER_ORDER", "gemini,groq")
    assert ask_service.answer_question("Any updates?") == NO_PROVIDER_MESSAGE


def test_gateway_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPSPILOT_FORCE_RULES", raising=False)
    monkeypatch.delenv("OPSPILOT_LLM_DISABLE", raising=False)

    def _fake_complete(**_kwargs):  # type: ignore[no-untyped-def]
        return CompletionResult(text=" Prioritize WI-001 ", provider="fake", model="fake-v1")

    monkeypatch.setattr(ask_service, "complete_prose", _fake_complete)
    assert ask_service.answer_question("What should I prioritize?") == "Prioritize WI-001"


def test_services_ask_is_public_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPSPILOT_FORCE_RULES", "1")
    assert ask_service.answer_question("hi") == UNAVAILABLE_MESSAGE
