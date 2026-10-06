"""Owner-run handshake probe: protocol version, tool names, session-id boolean.

Does not call tools. Does not print tokens, Authorization, or session-id values.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from collections.abc import Mapping

import httpx2
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.shared._httpx_utils import create_mcp_http_client
from mcp.types import Implementation

from opspilot.integrations.github_mcp.constants import (
    COPILOT_GATED_HINTS,
    DEFAULT_MCP_URL,
    HANDSHAKE_STDOUT_KEYS,
    PINNED_MCP_TOOLS,
    X_MCP_TOOLS_HEADER,
)

_TRUTHY = frozenset({"1", "true", "yes", "on"})


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in _TRUTHY


def format_handshake_lines(result: Mapping[str, str]) -> str:
    """Stable key=value lines; unknown keys dropped."""
    lines = [f"{key}={result[key]}" for key in sorted(result) if key in HANDSHAKE_STDOUT_KEYS]
    return "\n".join(lines)


def _readonly_headers() -> dict[str, str]:
    return {
        "X-MCP-Readonly": "true",
        "X-MCP-Lockdown": "true",
        "X-MCP-Tools": X_MCP_TOOLS_HEADER,
    }


async def run_handshake(
    *,
    url: str | None = None,
    token: str | None = None,
    http_client: httpx2.AsyncClient | None = None,
) -> dict[str, str]:
    """Initialize (or auto-negotiate) and tools/list. Never tools/call."""
    if _truthy("GITHUB_ACTIONS"):
        return {"error": "ci_blocked"}
    resolved_token = (token if token is not None else os.environ.get("GITHUB_MCP_PAT", "")).strip()
    if not resolved_token:
        return {"error": "missing_pat"}
    endpoint = (url or os.environ.get("OPSPILOT_GITHUB_MCP_URL") or DEFAULT_MCP_URL).strip()
    session_issued = {"v": False}

    async def _on_response(response: httpx2.Response) -> None:
        if response.headers.get("mcp-session-id"):
            session_issued["v"] = True

    owns_client = http_client is None
    client = http_client
    if client is None:
        headers = _readonly_headers()
        headers["Authorization"] = f"Bearer {resolved_token}"
        client = create_mcp_http_client(headers=headers)
        client.event_hooks.setdefault("response", []).append(_on_response)
    else:
        client.event_hooks.setdefault("response", []).append(_on_response)
        # Tests inject transport; still set readonly headers if missing.
        for key, value in _readonly_headers().items():
            client.headers.setdefault(key, value)
        client.headers.setdefault("Authorization", f"Bearer {resolved_token}")

    try:
        async with streamable_http_client(endpoint, http_client=client, terminate_on_close=True) as streams:
            read_stream, write_stream = streams
            async with ClientSession(
                read_stream,
                write_stream,
                client_info=Implementation(name="opspilot-handshake", version="0.1.0"),
            ) as session:
                init = await session.initialize()
                listed = await session.list_tools()
    except Exception as exc:  # noqa: BLE001 — map to a code; never interpolate token
        name = type(exc).__name__
        status = getattr(exc, "response", None)
        code = getattr(status, "status_code", None) if status is not None else None
        if code in {401, 403, 402, 404}:
            return {"error": f"http_{code}"}
        return {"error": f"handshake_failed:{name}"}
    finally:
        if owns_client:
            await client.aclose()

    names = [str(t.name) for t in listed.tools]
    pinned = [n for n in PINNED_MCP_TOOLS if n in names]
    gated = [n for n in names if any(h in n.lower() for h in COPILOT_GATED_HINTS)]
    protocol = str(init.protocol_version or "")
    return {
        "protocol_version": protocol,
        "session_id_issued": "yes" if session_issued["v"] else "no",
        "tool_count": str(len(names)),
        "tool_names": ",".join(names),
        "allowlisted_present": ",".join(pinned),
        "copilot_gated_advertised": "yes" if gated else "no",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GitHub MCP handshake probe (no tool calls).")
    parser.add_argument("--url", default=None, help="Override OPSPILOT_GITHUB_MCP_URL")
    args = parser.parse_args(argv)
    result = asyncio.run(run_handshake(url=args.url))
    sys.stdout.write(format_handshake_lines(result) + "\n")
    if "error" in result:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
