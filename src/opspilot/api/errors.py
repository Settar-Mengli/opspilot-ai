"""Uniform JSON error envelope for /api/v1 (and app-wide handlers)."""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from opspilot.llm.meta_redact import redact_text

_TRUTHY = frozenset({"1", "true", "yes", "on"})
logger = logging.getLogger("opspilot.api.errors")


def error_body(
    *,
    code: str,
    message: str,
    details: object | None = None,
    request_id: str | None = None,
) -> dict[str, object]:
    """Client-safe envelope: code + fixed message + request_id (never exception text)."""
    err: dict[str, object] = {"code": code, "message": message}
    if request_id:
        err["request_id"] = request_id
    if details is not None:
        err["details"] = details
    return {"error": err}


def _debug_errors_enabled() -> bool:
    return os.environ.get("OPSPILOT_DEBUG_ERRORS", "").strip().lower() in _TRUTHY


def sanitize_validation_details(errors: list[Any]) -> list[dict[str, Any]]:
    """F-03: codes/paths only unless OPSPILOT_DEBUG_ERRORS=1."""
    if _debug_errors_enabled():
        return list(errors)
    sanitized: list[dict[str, Any]] = []
    for item in errors:
        if not isinstance(item, dict):
            sanitized.append({"type": "validation_error"})
            continue
        sanitized.append(
            {
                "type": str(item.get("type", "validation_error")),
                "loc": item.get("loc", []),
            }
        )
    return sanitized


def _request_id_str(request: Request) -> str | None:
    rid = getattr(request.state, "request_id", None)
    return rid if isinstance(rid, str) and rid.strip() else None


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_body(
                code="validation_error",
                message="Request validation failed.",
                details=sanitize_validation_details(list(exc.errors())),
                request_id=_request_id_str(request),
            ),
        )

    @app.exception_handler(HTTPException)
    async def http_handler(request: Request, exc: HTTPException) -> JSONResponse:
        rid = _request_id_str(request)
        detail = exc.detail
        if isinstance(detail, dict) and "error" in detail and "message" in detail:
            code = str(detail["error"])
            message = str(detail["message"])
            details = detail.get("details")
            return JSONResponse(
                status_code=exc.status_code,
                content=error_body(code=code, message=message, details=details, request_id=rid),
            )
        if isinstance(detail, str):
            message = detail
        else:
            message = "Request failed."
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(code="http_error", message=message, request_id=rid),
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        rid = getattr(request.state, "request_id", None) or "-"
        logger.error(
            "unhandled_error request_id=%s error_code=%s message=%s",
            rid,
            type(exc).__name__,
            redact_text(str(exc), max_chars=200),
        )
        return JSONResponse(
            status_code=500,
            content=error_body(
                code="internal_error",
                message="An unexpected error occurred.",
                request_id=_request_id_str(request),
            ),
        )
