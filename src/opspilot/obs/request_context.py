"""Request-scoped contextvars (side-effect free — no logging, dotenv, or API imports)."""

from __future__ import annotations

import contextvars

request_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)
