"""Logging helpers with F-09 secret redaction."""

from __future__ import annotations

import logging
import re
from typing import Any

_SECRET_KEY_RE = re.compile(
    r"(api[_-]?key|token|password|secret|authorization|credential|refresh[_-]?token)",
    re.IGNORECASE,
)
_REDACTED = "***"


def redact_value(key: str, value: Any) -> Any:
    if _SECRET_KEY_RE.search(key):
        return _REDACTED
    if isinstance(value, str) and len(value) > 8 and value.lower().startswith(("sk-", "gsk_", "aq.")):
        return _REDACTED
    return value


def redact_fields(fields: dict[str, Any]) -> dict[str, Any]:
    return {k: redact_value(k, v) for k, v in fields.items()}


def configure_logging(level: int = logging.INFO) -> None:
    if logging.getLogger().handlers:
        logging.getLogger().setLevel(level)
        return

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    safe = redact_fields(fields)
    if safe:
        serialized_fields = " ".join(f"{key}={safe[key]}" for key in sorted(safe))
        logger.info("%s | %s", event, serialized_fields)
        return

    logger.info(event)
