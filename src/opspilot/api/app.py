"""FastAPI application — /api/v1 only."""

from __future__ import annotations

import contextvars
import logging
import re
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from opspilot.config.env_load import load_repo_dotenv

# Load repo .env before settings / DB resolve (existing process env wins).
load_repo_dotenv()

from opspilot.api.errors import register_exception_handlers  # noqa: E402
from opspilot.api.v1.oauth_routes import router as oauth_router  # noqa: E402
from opspilot.api.v1.routes import router as v1_router  # noqa: E402
from opspilot.api.v1.routes_ask import router as ask_router  # noqa: E402
from opspilot.api.v1.routes_mail import router as mail_router  # noqa: E402
from opspilot.persistence.db import log_active_database_host  # noqa: E402

LOCAL_UI_ORIGINS = [
    "http://127.0.0.1:5173",
]

request_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)

_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_access_logger = logging.getLogger("opspilot.api.access")


def normalize_request_id(incoming: str) -> str:
    """Accept client id if ≤64 chars and [A-Za-z0-9._-]; else regenerate."""
    candidate = incoming.strip()
    if candidate and _REQUEST_ID_RE.fullmatch(candidate):
        return candidate
    return str(uuid.uuid4())


class RequestIdFilter(logging.Filter):
    """Inject request_id from ContextVar into every LogRecord."""

    def filter(self, record: logging.LogRecord) -> bool:
        rid = request_id_ctx.get()
        record.request_id = rid or "-"
        return True


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Accept/generate X-Request-ID, access-log path-only, echo on response."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming = request.headers.get("X-Request-ID", "")
        request_id = normalize_request_id(incoming)
        request.state.request_id = request_id
        token = request_id_ctx.set(request_id)
        started = time.perf_counter()
        status_code = 500
        response: Response | None = None
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            latency_ms = int((time.perf_counter() - started) * 1000)
            # A3: path without query string; never log query params or bodies.
            _access_logger.info(
                "method=%s path=%s status=%s latency_ms=%s request_id=%s",
                request.method,
                request.url.path,
                status_code,
                latency_ms,
                request_id,
            )
            if response is not None:
                response.headers["X-Request-ID"] = request_id
            request_id_ctx.reset(token)


def create_app() -> FastAPI:
    load_repo_dotenv()
    log_active_database_host(logger=logging.getLogger("opspilot.api"))

    root = logging.getLogger()
    if not any(isinstance(f, RequestIdFilter) for f in root.filters):
        root.addFilter(RequestIdFilter())

    application = FastAPI(
        title="OpsPilot AI API",
        description="Local API for running and retrieving OpsPilot outputs.",
        version="0.1.0",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=LOCAL_UI_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-Request-ID"],
    )
    application.add_middleware(RequestIdMiddleware)
    register_exception_handlers(application)
    application.include_router(v1_router)
    application.include_router(ask_router, prefix="/api/v1")
    application.include_router(mail_router, prefix="/api/v1")
    application.include_router(oauth_router, prefix="/api/v1")
    return application


app = create_app()
