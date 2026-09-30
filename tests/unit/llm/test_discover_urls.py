"""Hermetic tests for discover URL helpers (MockTransport; no real sockets)."""

from __future__ import annotations

import httpx
import pytest

from opspilot.jobs import llm_discover
from opspilot.llm.providers.discover_urls import (
    gemini_models_list_url,
    ollama_tags_url,
    openai_compat_models_url,
)


def test_gemini_models_list_url() -> None:
    assert gemini_models_list_url() == "https://generativelanguage.googleapis.com/v1beta/models"


def test_openai_compat_models_urls() -> None:
    assert openai_compat_models_url("groq") == "https://api.groq.com/openai/v1/models"
    assert openai_compat_models_url("mistral") == "https://api.mistral.ai/v1/models"
    assert openai_compat_models_url("openrouter") == "https://openrouter.ai/api/v1/models"


def test_cloudflare_models_url_includes_account(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "acct-test")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "tok-test")
    url = openai_compat_models_url("cloudflare")
    assert "api.cloudflare.com" in url
    assert "acct-test" in url
    assert url.endswith("/models")


def test_ollama_tags_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    assert ollama_tags_url() == "http://127.0.0.1:11434/api/tags"
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11435")
    assert ollama_tags_url() == "http://127.0.0.1:11435/api/tags"


def test_discover_probe_uses_helpers_via_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INFERENCE_PROVIDER_ORDER", "gemini,groq")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini")
    monkeypatch.setenv("GROQ_API_KEY", "fake-groq")
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if "generativelanguage" in str(request.url):
            return httpx.Response(200, json={"models": []})
        return httpx.Response(200, json={"data": [{"id": "llama-test"}]})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)

    # Inject MockTransport client by patching httpx.Client used in discover
    orig_client = httpx.Client

    def _factory(*_a: object, **_k: object) -> httpx.Client:
        return client

    monkeypatch.setattr(httpx, "Client", _factory)
    try:
        rows = llm_discover.discover()
    finally:
        monkeypatch.setattr(httpx, "Client", orig_client)
        client.close()

    assert any("generativelanguage.googleapis.com" in u for u in seen)
    assert any("api.groq.com" in u for u in seen)
    by_name = {r["provider"]: r for r in rows}
    assert by_name["gemini"]["status_code"] == 200
    assert by_name["groq"]["status_code"] == 200
    assert "llama-test" in by_name["groq"].get("models_sample", [])
