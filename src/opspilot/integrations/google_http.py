"""Authorized Google HTTP helpers (injectable for hermetic tests)."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any, Protocol

import httpx

TOKEN_URL = "https://oauth2.googleapis.com/token"
_RETRYABLE_STATUSES = frozenset({429, 502, 503})
_BACKOFF_BASE_S = 0.5
_BACKOFF_SLEEP_CAP_S = 8.0
_BACKOFF_MAX_RETRIES = 3
_BACKOFF_WALL_CAP_S = 15.0


class GoogleHttpError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class GoogleTransport(Protocol):
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response: ...


class HttpxTransport:
    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        client = self._client or httpx.Client(timeout=30.0)
        owns = self._client is None
        try:
            return client.request(method, url, headers=headers, params=params, data=data, json=json)
        finally:
            if owns:
                client.close()


def _retry_after_delay(resp: httpx.Response, attempt: int) -> float:
    raw = resp.headers.get("Retry-After") or resp.headers.get("retry-after")
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = float(raw.strip())
        except ValueError:
            parsed = None
        if parsed is not None:
            return float(min(_BACKOFF_SLEEP_CAP_S, max(0.0, parsed)))
    delay = _BACKOFF_BASE_S * float(2**attempt)
    return float(min(_BACKOFF_SLEEP_CAP_S, delay))


def request_with_backoff(
    transport: GoogleTransport,
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> httpx.Response:
    """Retry 429/502/503 with exponential backoff; total sleep capped at 15s."""
    slept = 0.0
    last: httpx.Response | None = None
    for attempt in range(_BACKOFF_MAX_RETRIES + 1):
        last = transport.request(method, url, headers=headers, params=params, data=data, json=json)
        if last.status_code not in _RETRYABLE_STATUSES or attempt >= _BACKOFF_MAX_RETRIES:
            return last
        delay = _retry_after_delay(last, attempt)
        if slept + delay > _BACKOFF_WALL_CAP_S:
            return last
        sleep(delay)
        slept += delay
    assert last is not None
    return last


def refresh_access_token(
    *,
    client_id: str,
    client_secret: str,
    refresh_token: str,
    transport: GoogleTransport,
) -> str:
    resp = transport.request(
        "POST",
        TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
    )
    if resp.status_code >= 400:
        err_code: str | None = None
        try:
            payload = resp.json()
            if isinstance(payload, dict):
                raw_err = payload.get("error")
                if isinstance(raw_err, str):
                    err_code = raw_err
        except Exception:
            err_code = None
        if resp.status_code == 400 and err_code == "invalid_grant":
            raise GoogleHttpError("invalid_grant", status_code=400)
        raise GoogleHttpError("refresh_failed", status_code=resp.status_code)
    payload = resp.json()
    access = str(payload.get("access_token") or "").strip()
    if not access:
        raise GoogleHttpError("refresh_missing_access")
    return access
