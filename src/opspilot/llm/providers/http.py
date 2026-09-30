"""Shared httpx helpers for LLM providers."""

from __future__ import annotations

import httpx

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
