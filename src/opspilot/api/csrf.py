"""CSRF Origin/Referer checks for cookie-auth mutating routes."""

from __future__ import annotations

import os
from urllib.parse import urlparse

from fastapi import Request

from opspilot.api.schemas import safe_error

# Keep in sync with opspilot.api.app.LOCAL_UI_ORIGINS
_DEFAULT_UI_ORIGINS = frozenset({"http://127.0.0.1:5173"})


def _allowed_origins() -> frozenset[str]:
    raw = os.environ.get("OPSPILOT_CORS_ORIGINS", "").strip()
    if raw:
        return frozenset(part.strip().rstrip("/") for part in raw.split(",") if part.strip())
    return _DEFAULT_UI_ORIGINS


def _is_dev_relaxed() -> bool:
    """Dev-only relaxation when OPSPILOT_CSRF_RELAX_DEV=1 (local hermetic / TestClient)."""
    return os.environ.get("OPSPILOT_CSRF_RELAX_DEV", "").strip().lower() in {"1", "true", "yes"}


def _origin_from_request(request: Request) -> str | None:
    origin = (request.headers.get("origin") or "").strip()
    if origin:
        return origin.rstrip("/")
    referer = (request.headers.get("referer") or "").strip()
    if not referer:
        return None
    parsed = urlparse(referer)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")


def require_csrf_origin(request: Request) -> None:
    """Fail closed when Origin/Referer missing or not allowlisted (unless relax-dev)."""
    if _is_dev_relaxed():
        return
    allowed = _allowed_origins()
    origin = _origin_from_request(request)
    if origin is None or origin not in allowed:
        raise safe_error(403, "csrf_origin_rejected", "Origin not allowed.")
