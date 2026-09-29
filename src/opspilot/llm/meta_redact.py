"""Redact and truncate LLM error/meta payloads (F-09 aligned)."""

from __future__ import annotations

import re
from typing import Any

from opspilot.utils.logging_utils import redact_fields

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_BEARER_RE = re.compile(r"(?i)\b(bearer|api[_-]?key|token)\s*[:=]\s*\S+")
_KEYISH_RE = re.compile(r"\b(?:sk-[A-Za-z0-9_-]{8,}|gsk_[A-Za-z0-9_-]{8,}|AQ\.[A-Za-z0-9_-]{8,})\b")


def redact_text(text: str, *, max_chars: int) -> str:
    """Redact secrets/emails in free text and truncate."""
    if not text:
        return ""
    out = _EMAIL_RE.sub("***", text)
    out = _BEARER_RE.sub(r"\1=***", out)
    out = _KEYISH_RE.sub("***", out)
    if len(out) > max_chars:
        out = out[:max_chars]
    return out


def http_error_meta(*, status_code: int, body: str) -> dict[str, Any]:
    return {
        "status_code": status_code,
        "provider_error": redact_text(body, max_chars=500),
    }


def parse_failure_meta(
    *,
    error_class: str,
    validation_error: str,
    raw_output: str,
) -> dict[str, Any]:
    return {
        "error_class": error_class,
        "validation_error": redact_text(validation_error, max_chars=500),
        "output_len": len(raw_output),
        "output_head": redact_text(raw_output, max_chars=300),
    }


def sanitize_meta(meta: dict[str, Any] | None) -> dict[str, Any]:
    """Field-name redaction + string truncation for nested meta."""
    if not meta:
        return {}
    redacted = redact_fields(meta)
    out: dict[str, Any] = {}
    for key, value in redacted.items():
        if isinstance(value, str) and key in {"provider_error", "validation_error"}:
            out[key] = redact_text(value, max_chars=500)
        elif isinstance(value, str) and key == "output_head":
            out[key] = redact_text(value, max_chars=300)
        else:
            out[key] = value
    return out
