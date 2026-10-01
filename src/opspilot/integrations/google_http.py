"""Authorized Google HTTP helpers (injectable for hermetic tests)."""

from __future__ import annotations

from typing import Any, Protocol

import httpx

TOKEN_URL = "https://oauth2.googleapis.com/token"


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
        raise GoogleHttpError("refresh_failed", status_code=resp.status_code)
    payload = resp.json()
    access = str(payload.get("access_token") or "").strip()
    if not access:
        raise GoogleHttpError("refresh_missing_access")
    return access
