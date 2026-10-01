"""OAuth API routes (B4 C3). Sync lands in C4."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from opspilot.api.deps import get_db_session
from opspilot.api.schemas import safe_error
from opspilot.integrations.google_oauth import (
    GoogleOAuthError,
    complete_oauth,
    start_pkce,
)
from opspilot.persistence.crypto import EncryptionUnavailableError
from opspilot.persistence.repositories import oauth_credentials
from opspilot.services.operator_session import (
    SessionUnavailableError,
    demo_mode_enabled,
    set_operator_cookie,
)

router = APIRouter(tags=["oauth"])

_PKCE_COOKIE = "opspilot_pkce"
_FE_AFTER_OAUTH = os.environ.get("OPSPILOT_FE_ORIGIN", "http://127.0.0.1:5173").rstrip("/") + "/connections"


@router.get("/oauth/google/start")
def oauth_google_start() -> RedirectResponse:
    if demo_mode_enabled():
        raise safe_error(403, "demo_mode_blocks_oauth", "DEMO_MODE blocks Google OAuth.")
    try:
        start = start_pkce()
    except GoogleOAuthError as exc:
        raise safe_error(503, "oauth_misconfigured", "Google OAuth is not configured.") from exc
    response = RedirectResponse(url=start.authorization_url, status_code=302)
    response.set_cookie(
        key=_PKCE_COOKIE,
        value=f"{start.state}:{start.code_verifier}",
        max_age=600,
        httponly=True,
        secure=False,
        samesite="lax",
        path="/",
    )
    return response


@router.get("/oauth/google/callback")
def oauth_google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    session: Session = Depends(get_db_session),
) -> RedirectResponse:
    if demo_mode_enabled():
        raise safe_error(403, "demo_mode_blocks_oauth", "DEMO_MODE blocks Google OAuth.")
    if error:
        raise safe_error(400, "oauth_denied", "Google OAuth was denied.")
    if not code or not state:
        raise safe_error(400, "oauth_invalid_callback", "Missing OAuth code or state.")
    raw = request.cookies.get(_PKCE_COOKIE) or ""
    if ":" not in raw:
        raise safe_error(400, "oauth_pkce_missing", "PKCE session missing; restart connect.")
    saved_state, verifier = raw.split(":", 1)
    if saved_state != state or not verifier:
        raise safe_error(400, "oauth_state_mismatch", "OAuth state mismatch.")
    try:
        bundle = complete_oauth(code=code, code_verifier=verifier)
        oauth_credentials.upsert_encrypted_refresh(
            session,
            provider="google",
            account_email=bundle.email,
            scopes=bundle.scopes,
            refresh_token_plaintext=bundle.refresh_token,
        )
    except EncryptionUnavailableError as exc:
        raise safe_error(503, "encryption_unavailable", "Token encryption unavailable.") from exc
    except GoogleOAuthError as exc:
        raise safe_error(502, "oauth_exchange_failed", "Google token exchange failed.") from exc
    except SessionUnavailableError as exc:
        raise safe_error(503, "session_unavailable", "Session signing unavailable.") from exc

    response = RedirectResponse(url=_FE_AFTER_OAUTH, status_code=302)
    set_operator_cookie(response, email=bundle.email)
    response.delete_cookie(_PKCE_COOKIE, path="/")
    return response
