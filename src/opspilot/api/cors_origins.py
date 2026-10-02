"""Shared CORS / CSRF allowed origin parsing (OPSPILOT_CORS_ORIGINS)."""

from __future__ import annotations

import os

DEFAULT_UI_ORIGIN = "http://127.0.0.1:5173"
_DEFAULT_UI_ORIGINS = frozenset({DEFAULT_UI_ORIGIN})


def allowed_cors_origins() -> list[str]:
    """Return allowlist as a list (CORSMiddleware). Same parse rules as CSRF."""
    return sorted(allowed_cors_origins_set())


def allowed_cors_origins_set() -> frozenset[str]:
    raw = os.environ.get("OPSPILOT_CORS_ORIGINS", "").strip()
    if raw:
        return frozenset(part.strip().rstrip("/") for part in raw.split(",") if part.strip())
    return _DEFAULT_UI_ORIGINS
