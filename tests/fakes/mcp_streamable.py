"""In-process Streamable HTTP MCP fake for hermetic tests (protocol boundary)."""

from __future__ import annotations

from typing import Any

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from opspilot.integrations.github_mcp.constants import PINNED_MCP_TOOLS

PROTOCOL_VERSION = "2025-11-25"


def _tool(name: str) -> dict[str, Any]:
    return {
        "name": name,
        "description": f"fake {name}",
        "inputSchema": {"type": "object", "additionalProperties": True},
    }


def make_fake_mcp_app(
    *,
    extra_tool_names: tuple[str, ...] = ("create_issue",),
    session_id: str = "fake-session-1",
    call_handler: Any | None = None,
    hang_tools_call: bool = False,
    protocol_version: str = PROTOCOL_VERSION,
) -> Starlette:
    """JSON Streamable HTTP MCP (initialize-era) plus optional tools/call."""

    advertised = list(PINNED_MCP_TOOLS) + list(extra_tool_names)

    async def mcp_endpoint(request: Request) -> Response:
        if request.method == "GET":
            return Response(status_code=405)
        if request.method == "DELETE":
            return Response(status_code=204)
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            return JSONResponse({"jsonrpc": "2.0", "error": {"code": -32700, "message": "parse"}}, status_code=400)
        method = str(body.get("method") or "")
        req_id = body.get("id")
        if method == "notifications/initialized":
            return Response(status_code=202)
        if method == "server/discover":
            return JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": "Method not found"},
                }
            )
        if method == "initialize":
            return JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": protocol_version,
                        "capabilities": {"tools": {"listChanged": False}},
                        "serverInfo": {"name": "fake-github-mcp", "version": "0"},
                    },
                },
                headers={"mcp-session-id": session_id},
            )
        if method == "tools/list":
            return JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"tools": [_tool(n) for n in advertised]},
                }
            )
        if method == "tools/call":
            if hang_tools_call:
                import asyncio

                await asyncio.sleep(3600)
            params = body.get("params") or {}
            if call_handler is not None:
                payload = call_handler(params)
            else:
                payload = {
                    "content": [{"type": "text", "text": "ok"}],
                    "isError": False,
                }
            return JSONResponse({"jsonrpc": "2.0", "id": req_id, "result": payload})
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": "Method not found"},
            }
        )

    return Starlette(routes=[Route("/mcp", mcp_endpoint, methods=["GET", "POST", "DELETE"])])
