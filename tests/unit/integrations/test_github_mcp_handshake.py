"""Hermetic GitHub MCP handshake tests (fake Streamable HTTP; no live GitHub)."""

from __future__ import annotations

import asyncio
import io
from contextlib import redirect_stdout

import httpx2
import pytest
from tests.fakes.mcp_streamable import make_fake_mcp_app

from opspilot.integrations.github_mcp.constants import HANDSHAKE_STDOUT_KEYS, PINNED_MCP_TOOLS
from opspilot.integrations.github_mcp.handshake import format_handshake_lines, main, run_handshake

_LEAK = "github_pat_TESTLEAKTOKENVALUE99"


def _client() -> httpx2.AsyncClient:
    app = make_fake_mcp_app()
    transport = httpx2.ASGITransport(app=app)
    return httpx2.AsyncClient(transport=transport, base_url="http://test")


def test_handshake_records_version_tools_session_no_tool_call(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)

    async def _run() -> dict[str, str]:
        async with _client() as client:
            return await run_handshake(url="http://test/mcp", token=_LEAK, http_client=client)

    result = asyncio.run(_run())
    assert result["protocol_version"] == "2025-11-25"
    assert result["session_id_issued"] == "yes"
    assert result["allowlisted_present"] == ",".join(PINNED_MCP_TOOLS)
    assert "create_issue" in result["tool_names"]
    assert "error" not in result
    text = format_handshake_lines(result)
    assert _LEAK not in text
    assert "Authorization" not in text
    assert "fake-session-1" not in text
    for line in text.splitlines():
        key = line.split("=", 1)[0]
        assert key in HANDSHAKE_STDOUT_KEYS


def test_handshake_missing_pat_no_http(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_MCP_PAT", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)

    class Boom(httpx2.AsyncClient):
        async def send(self, request: httpx2.Request, **kwargs):  # type: ignore[no-untyped-def]
            raise AssertionError("http_attempted")

    result = asyncio.run(run_handshake(url="http://test/mcp", token="", http_client=Boom()))
    assert result == {"error": "missing_pat"}


def test_handshake_ci_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    result = asyncio.run(run_handshake(url="http://test/mcp", token=_LEAK))
    assert result == {"error": "ci_blocked"}


def test_handshake_cli_stdout_omits_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.setenv("GITHUB_MCP_PAT", _LEAK)
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = main(["--url", "http://127.0.0.1:1/mcp"])
    out = buf.getvalue()
    assert code == 2
    assert _LEAK not in out
    assert "error=" in out
