"""FastAPI application — /api/v1 only."""

from __future__ import annotations

import contextvars
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from opspilot.api.errors import register_exception_handlers
from opspilot.api.v1.routes import router as v1_router

LOCAL_UI_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

request_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """B-03: accept or generate X-Request-ID and echo on the response."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming = request.headers.get("X-Request-ID", "").strip()
        request_id = incoming or str(uuid.uuid4())
        request.state.request_id = request_id
        token = request_id_ctx.set(request_id)
        try:
            response = await call_next(request)
        finally:
            request_id_ctx.reset(token)
        response.headers["X-Request-ID"] = request_id
        return response


def create_app() -> FastAPI:
    application = FastAPI(
        title="OpsPilot AI API",
        description="Local API for running and retrieving OpsPilot outputs.",
        version="0.1.0",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=LOCAL_UI_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Request-ID"],
    )
    application.add_middleware(RequestIdMiddleware)
    register_exception_handlers(application)
    application.include_router(v1_router)
    return application


app = create_app()
