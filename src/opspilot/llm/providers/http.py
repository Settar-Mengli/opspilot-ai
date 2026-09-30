"""Shared httpx helpers for LLM providers."""

from __future__ import annotations

import httpx

from opspilot.llm.meta_redact import http_error_meta
from opspilot.llm.types import AttemptStatus, ProviderResult

CONNECT_TIMEOUT_S = 10.0
READ_TIMEOUT_S = 30.0


def default_timeout() -> httpx.Timeout:
    return httpx.Timeout(READ_TIMEOUT_S, connect=CONNECT_TIMEOUT_S)


def parse_retry_after(response: httpx.Response) -> float | None:
    raw = response.headers.get("Retry-After")
    if not raw:
        return None
    try:
        return float(raw.strip())
    except ValueError:
        return None


def map_http_provider_result(
    *,
    response: httpx.Response,
    model: str,
    latency_ms: int,
) -> ProviderResult | None:
    """Map HTTP 429 / ≥400 to ProviderResult; return None for success status codes."""
    if response.status_code == 429:
        return ProviderResult(
            status=AttemptStatus.RATE_LIMITED,
            model=model,
            error_code="429",
            retry_after_s=parse_retry_after(response),
            latency_ms=latency_ms,
        )
    if response.status_code >= 400:
        return ProviderResult(
            status=AttemptStatus.ERROR,
            model=model,
            error_code=f"http_{response.status_code}",
            latency_ms=latency_ms,
            meta=http_error_meta(status_code=response.status_code, body=response.text),
        )
    return None
