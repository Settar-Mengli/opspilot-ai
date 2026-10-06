"""Streamable HTTP GitHub MCP adapter. Timeout and neutralization live here, not in execute_tool."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections.abc import Callable
from typing import Any

import httpx2
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.shared._httpx_utils import create_mcp_http_client
from mcp.shared.exceptions import MCPError
from mcp.types import Implementation

from opspilot.integrations.github_mcp.constants import (
    DEFAULT_MCP_URL,
    DEFAULT_TIMEOUT_S,
    EXPECTED_PROTOCOL_VERSION,
    PINNED_MCP_TOOLS,
    X_MCP_TOOLS_HEADER,
)
from opspilot.integrations.github_mcp.gate import github_mcp_timeout_s
from opspilot.llm.prompt_safety import neutralize_text

_logger = logging.getLogger("opspilot.integrations.github_mcp")

HttpClientFactory = Callable[..., httpx2.AsyncClient]
_http_client_factory: HttpClientFactory | None = None


def set_http_client_factory(factory: HttpClientFactory | None) -> None:
    """Tests inject ASGI/httpx2 at the protocol boundary. Production leaves this None."""
    global _http_client_factory
    _http_client_factory = factory


def _readonly_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-MCP-Readonly": "true",
        "X-MCP-Lockdown": "true",
        "X-MCP-Tools": X_MCP_TOOLS_HEADER,
    }


def build_async_client(*, token: str, timeout_s: float) -> httpx2.AsyncClient:
    if _http_client_factory is not None:
        return _http_client_factory(token=token, timeout_s=timeout_s)
    timeout = httpx2.Timeout(timeout_s, read=timeout_s)
    return create_mcp_http_client(headers=_readonly_headers(token), timeout=timeout)


def _content_text(result: Any) -> str:
    parts: list[str] = []
    content = getattr(result, "content", None) or []
    for item in content:
        text = getattr(item, "text", None)
        if text:
            parts.append(str(text))
    if not parts:
        structured = getattr(result, "structuredContent", None) or getattr(result, "structured_content", None)
        if structured is not None:
            parts.append(json.dumps(structured, ensure_ascii=False))
    return "\n".join(parts)


def _map_call_result(tool: str, result: Any) -> dict[str, Any]:
    if getattr(result, "isError", False) or getattr(result, "is_error", False):
        return {"ok": False, "error": "mcp_tool_error"}
    raw = _content_text(result)
    if tool == "get_me":
        login = ""
        ident = ""
        try:
            data = json.loads(raw) if raw.strip().startswith("{") else {}
        except json.JSONDecodeError:
            data = {}
        if isinstance(data, dict):
            login = neutralize_text(str(data.get("login") or data.get("name") or raw))[:64]
            ident = neutralize_text(str(data.get("id") or ""))[:64]
        else:
            login = neutralize_text(raw)[:64]
        return {"ok": True, "login": login, "id": ident}
    if tool == "get_file_contents":
        return {"ok": True, "path": "", "text": neutralize_text(raw)[:2000]}
    if tool == "list_commits":
        commits: list[dict[str, str]] = []
        try:
            parsed: Any = json.loads(raw) if raw.strip().startswith("[") or raw.strip().startswith("{") else raw
        except json.JSONDecodeError:
            parsed = raw
        rows: list[Any]
        if isinstance(parsed, dict) and isinstance(parsed.get("commits"), list):
            rows = parsed["commits"]
        elif isinstance(parsed, list):
            rows = parsed
        else:
            rows = [{"message": str(parsed)[:200]}]
        for row in rows[:20]:
            if isinstance(row, dict):
                commits.append(
                    {
                        "sha": neutralize_text(str(row.get("sha") or row.get("oid") or ""))[:40],
                        "message": neutralize_text(str(row.get("message") or row.get("text") or ""))[:200],
                        "date": neutralize_text(str(row.get("date") or row.get("committedDate") or ""))[:40],
                    }
                )
            else:
                commits.append({"sha": "", "message": neutralize_text(str(row))[:200], "date": ""})
        return {"ok": True, "commits": commits}
    if tool == "pull_request_read":
        title = ""
        state = ""
        body = raw
        number = 0
        try:
            data = json.loads(raw) if raw.strip().startswith("{") else {}
        except json.JSONDecodeError:
            data = {}
        if isinstance(data, dict) and data:
            title = str(data.get("title") or "")
            state = str(data.get("state") or "")
            body = str(data.get("body") or raw)
            try:
                number = int(data.get("number") or data.get("pullNumber") or 0)
            except (TypeError, ValueError):
                number = 0
        return {
            "ok": True,
            "number": number,
            "title": neutralize_text(title)[:200],
            "state": neutralize_text(state)[:32],
            "body": neutralize_text(body)[:500],
        }
    return {"ok": False, "error": "unknown_tool"}


def _map_http_status_error(exc: httpx2.HTTPStatusError) -> dict[str, Any]:
    # Never str(exc) / never dump request — Authorization lives on the request object.
    status = int(getattr(getattr(exc, "response", None), "status_code", 0) or 0)
    _logger.info("github_mcp_call_failed error_code=HTTPStatusError status_class=%s", status // 100)
    if 400 <= status < 500:
        return {"ok": False, "error": "mcp_http_4xx"}
    if 500 <= status < 600:
        return {"ok": False, "error": "mcp_http_5xx"}
    return {"ok": False, "error": "mcp_http_error"}


def _find_http_status_error(exc: BaseException) -> httpx2.HTTPStatusError | None:
    if isinstance(exc, httpx2.HTTPStatusError):
        return exc
    if isinstance(exc, BaseExceptionGroup):
        for nested in exc.exceptions:
            found = _find_http_status_error(nested)
            if found is not None:
                return found
    cause = exc.__cause__ or exc.__context__
    if isinstance(cause, BaseException):
        return _find_http_status_error(cause)
    return None


async def _call_tool_async(*, tool: str, arguments: dict[str, Any], token: str, timeout_s: float) -> dict[str, Any]:
    if tool not in PINNED_MCP_TOOLS:
        return {"ok": False, "error": "unknown_tool"}
    url = (os.environ.get("OPSPILOT_GITHUB_MCP_URL") or DEFAULT_MCP_URL).strip()
    client = build_async_client(token=token, timeout_s=timeout_s)
    owns = _http_client_factory is None
    try:
        async with asyncio.timeout(timeout_s):
            async with streamable_http_client(url, http_client=client, terminate_on_close=True) as streams:
                read_stream, write_stream = streams
                async with ClientSession(
                    read_stream,
                    write_stream,
                    client_info=Implementation(name="opspilot", version="0.1.0"),
                ) as session:
                    try:
                        init_result = await session.initialize()
                    except RuntimeError as exc:
                        # SDK raises before return when the version is outside HANDSHAKE_PROTOCOL_VERSIONS.
                        # args[0] is a version string only — never log it; match for the distinct code.
                        msg = exc.args[0] if exc.args and isinstance(exc.args[0], str) else ""
                        if "Unsupported protocol version" in msg:
                            return {"ok": False, "error": "mcp_protocol_version_mismatch"}
                        raise
                    negotiated = str(getattr(init_result, "protocol_version", "") or "")
                    if negotiated != EXPECTED_PROTOCOL_VERSION:
                        return {"ok": False, "error": "mcp_protocol_version_mismatch"}
                    result = await session.call_tool(tool, arguments)
                    return _map_call_result(tool, result)
    except TimeoutError:
        return {"ok": False, "error": "mcp_timeout"}
    except httpx2.TimeoutException:
        return {"ok": False, "error": "mcp_timeout"}
    except httpx2.HTTPStatusError as exc:
        return _map_http_status_error(exc)
    except MCPError:
        return {"ok": False, "error": "mcp_protocol_error"}
    except Exception as exc:  # noqa: BLE001 — never interpolate token
        http_exc = _find_http_status_error(exc)
        if http_exc is not None:
            return _map_http_status_error(http_exc)
        _logger.info("github_mcp_call_failed error_code=%s", type(exc).__name__)
        return {"ok": False, "error": "mcp_protocol_error"}
    finally:
        if owns:
            await client.aclose()


def call_pinned_tool(tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Sync entry for Ask tools. Bounds wall time with asyncio.wait_for (not SQLAlchemy)."""
    token = os.environ.get("GITHUB_MCP_PAT", "").strip()
    timeout_s = github_mcp_timeout_s() or DEFAULT_TIMEOUT_S
    try:
        return asyncio.run(_call_tool_async(tool=tool, arguments=arguments, token=token, timeout_s=timeout_s))
    except TimeoutError:
        return {"ok": False, "error": "mcp_timeout"}
