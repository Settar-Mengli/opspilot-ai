"""Unit tests for llm_discover stub (hermetic)."""

from __future__ import annotations

import httpx
import pytest

from opspilot.jobs import llm_discover


def test_probe_gemini_uses_header_not_query_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    def handler(request: httpx.Request) -> httpx.Response:
        assert "key" not in request.url.params
        assert "key=" not in str(request.url)
        assert request.headers.get("x-goog-api-key") == "test-key"
        return httpx.Response(200, json={"models": []})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    try:
        result = llm_discover._probe_gemini(client, "test-key")
    finally:
        client.close()
    assert result["status_code"] == 200
    assert result["reachable"] is True


def test_discover_without_keys_skips_http(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INFERENCE_PROVIDER_ORDER", "gemini,groq")
    for key in ("GEMINI_API_KEY", "GROQ_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("OPSPILOT_ANTHROPIC_ENABLED", "false")

    class _Boom:
        def __init__(self, *a, **k):  # type: ignore[no-untyped-def]
            raise AssertionError("httpx.Client must not open without keys")

    monkeypatch.setattr(llm_discover.httpx, "Client", _Boom)
    rows = llm_discover.discover()
    by_name = {r["provider"]: r for r in rows}
    assert by_name["gemini"]["configured"] is False
    assert by_name["groq"]["configured"] is False
    assert by_name["anthropic"]["enabled"] is False


def test_key_format_warning_gemini() -> None:
    assert llm_discover._key_format_warning("gemini", "AQ.abc") is not None
    assert llm_discover._key_format_warning("gemini", "normal") is None
