"""Google OAuth authorization-code + PKCE (Testing forever, D-016)."""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlencode

import httpx

SCOPES = (
    "openid",
    "email",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
)

REQUIRED_SCOPES = frozenset(
    {
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/calendar.readonly",
    }
)

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"

DEFAULT_REDIRECT_URI = "http://127.0.0.1:8000/api/v1/oauth/google/callback"

GRANT_REQUIRED_MESSAGE = "Grant Gmail and Calendar access to continue"


class GoogleOAuthError(RuntimeError):
    """OAuth configuration or token exchange failure."""


class IncompleteGrantError(GoogleOAuthError):
    """Token response missing required Gmail/Calendar scopes (or omitted scope entirely)."""


@dataclass(frozen=True)
class PkceStart:
    authorization_url: str
    state: str
    code_verifier: str


@dataclass(frozen=True)
class TokenBundle:
    refresh_token: str
    access_token: str
    email: str
    scopes: str


class TokenExchanger(Protocol):
    def exchange(self, *, code: str, code_verifier: str, redirect_uri: str) -> dict[str, Any]: ...

    def fetch_email(self, *, access_token: str) -> str: ...


def redirect_uri() -> str:
    return os.environ.get("GOOGLE_OAUTH_REDIRECT_URI", DEFAULT_REDIRECT_URI).strip() or DEFAULT_REDIRECT_URI


def client_id() -> str:
    value = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "").strip()
    if not value:
        raise GoogleOAuthError("GOOGLE_OAUTH_CLIENT_ID is not set")
    return value


def client_secret() -> str:
    value = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
    if not value:
        raise GoogleOAuthError("GOOGLE_OAUTH_CLIENT_SECRET is not set")
    return value


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def make_pkce_pair() -> tuple[str, str]:
    verifier = _b64url(secrets.token_bytes(32))
    challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge


def build_authorization_url(*, state: str, code_challenge: str) -> str:
    params = {
        "client_id": client_id(),
        "redirect_uri": redirect_uri(),
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "access_type": "offline",
        "prompt": "consent",
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def start_pkce() -> PkceStart:
    state = _b64url(secrets.token_bytes(24))
    verifier, challenge = make_pkce_pair()
    return PkceStart(
        authorization_url=build_authorization_url(state=state, code_challenge=challenge),
        state=state,
        code_verifier=verifier,
    )


class HttpTokenExchanger:
    """Live Google token endpoints (never used in hermetic CI)."""

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client

    def exchange(self, *, code: str, code_verifier: str, redirect_uri: str) -> dict[str, Any]:
        client = self._client or httpx.Client(timeout=30.0)
        owns = self._client is None
        try:
            resp = client.post(
                TOKEN_URL,
                data={
                    "client_id": client_id(),
                    "client_secret": client_secret(),
                    "code": code,
                    "code_verifier": code_verifier,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
            )
            if resp.status_code >= 400:
                raise GoogleOAuthError("token_exchange_failed")
            payload = resp.json()
            if not isinstance(payload, dict):
                raise GoogleOAuthError("token_exchange_invalid")
            return payload
        finally:
            if owns:
                client.close()

    def fetch_email(self, *, access_token: str) -> str:
        client = self._client or httpx.Client(timeout=30.0)
        owns = self._client is None
        try:
            resp = client.get(USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"})
            if resp.status_code >= 400:
                raise GoogleOAuthError("userinfo_failed")
            payload = resp.json()
            email = str(payload.get("email") or "").strip()
            if not email:
                raise GoogleOAuthError("userinfo_missing_email")
            return email
        finally:
            if owns:
                client.close()


def parse_scopes(scopes: str) -> set[str]:
    """Split a space- or comma-separated scope string into a set of tokens."""
    return {part.strip() for part in scopes.replace(",", " ").split() if part.strip()}


def has_required_scopes(scopes: str) -> bool:
    """True when both gmail.readonly and calendar.readonly are present."""
    return REQUIRED_SCOPES.issubset(parse_scopes(scopes))


def complete_oauth(
    *,
    code: str,
    code_verifier: str,
    exchanger: TokenExchanger | None = None,
) -> TokenBundle:
    ex = exchanger or HttpTokenExchanger()
    payload = ex.exchange(code=code, code_verifier=code_verifier, redirect_uri=redirect_uri())
    refresh = str(payload.get("refresh_token") or "").strip()
    access = str(payload.get("access_token") or "").strip()
    if not refresh or not access:
        raise GoogleOAuthError("missing_tokens")
    # Never invent scopes when the token response omits `scope`.
    if "scope" not in payload or payload.get("scope") is None:
        raise IncompleteGrantError("missing_scope")
    scope = str(payload.get("scope") or "").strip()
    if not scope:
        raise IncompleteGrantError("missing_scope")
    if not has_required_scopes(scope):
        raise IncompleteGrantError("incomplete_grant")
    email = ex.fetch_email(access_token=access)
    return TokenBundle(refresh_token=refresh, access_token=access, email=email, scopes=scope)
