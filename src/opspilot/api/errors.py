"""Uniform JSON error envelope for /api/v1 (and app-wide handlers)."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def error_body(*, code: str, message: str, details: object | None = None) -> dict[str, object]:
    err: dict[str, object] = {"code": code, "message": message}
    if details is not None:
        err["details"] = details
    return {"error": err}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_body(
                code="validation_error",
                message="Request validation failed.",
                details=exc.errors(),
            ),
        )

    @app.exception_handler(HTTPException)
    async def http_handler(_request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict) and "error" in detail and "message" in detail:
            code = str(detail["error"])
            message = str(detail["message"])
            return JSONResponse(
                status_code=exc.status_code,
                content=error_body(code=code, message=message),
            )
        if isinstance(detail, str):
            message = detail
        else:
            message = "Request failed."
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(code="http_error", message=message),
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(_request: Request, _exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content=error_body(
                code="internal_error",
                message="An unexpected error occurred.",
            ),
        )
