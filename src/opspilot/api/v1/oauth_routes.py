"""OAuth + sync API routes (B4)."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from opspilot.api.csrf import require_csrf_origin
from opspilot.api.deps import get_db_session
from opspilot.api.schemas import SyncResponse, safe_error
from opspilot.integrations.google_http import GoogleHttpError
from opspilot.integrations.google_oauth import (
    GoogleOAuthError,
    IncompleteGrantError,
    complete_oauth,
    revoke_refresh_token,
    start_pkce,
)
from opspilot.persistence.crypto import EncryptionUnavailableError
from opspilot.persistence.repositories import oauth_credentials, sync_cursors
from opspilot.services import google_sync
from opspilot.services.operator_session import (
    COOKIE_NAME,
    SessionUnavailableError,
    clear_operator_cookie,
    demo_mode_enabled,
    set_operator_cookie,
    verify_session,
)

router = APIRouter(tags=["oauth"])

_PKCE_COOKIE = "opspilot_pkce"
_FE_CONNECTIONS = os.environ.get("OPSPILOT_FE_ORIGIN", "http://127.0.0.1:5173").rstrip("/") + "/connections"
_FE_AFTER_OAUTH = _FE_CONNECTIONS
_FE_GRANT_REQUIRED = _FE_CONNECTIONS + "?oauth_error=grant_required"


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
    except IncompleteGrantError:
        # Do not store a partial credential; send operator back to Connections with copy.
        response = RedirectResponse(url=_FE_GRANT_REQUIRED, status_code=302)
        response.delete_cookie(_PKCE_COOKIE, path="/")
        return response
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


@router.post("/sync", response_model=SyncResponse)
def post_sync(request: Request, session: Session = Depends(get_db_session)) -> SyncResponse:
    if demo_mode_enabled():
        raise safe_error(403, "demo_mode_blocks_sync", "DEMO_MODE blocks sync.")
    sess = verify_session(request.cookies.get(COOKIE_NAME))
    if sess is None:
        raise safe_error(401, "operator_auth_required", "Operator session required.")
    try:
        sync_result = google_sync.run_sync(session)
        # G6: persist sync before triage so a triage timeout cannot roll back mail/meetings/cursors.
        session.commit()
        from opspilot.api.services.gmail_triage import triage_connected_gmail_fresh

        triaged = triage_connected_gmail_fresh()
        return SyncResponse(
            account_email=str(sync_result.get("account_email") or ""),
            gmail_upserted=int(sync_result.get("gmail_upserted") or 0),
            gmail_removed=int(sync_result.get("gmail_removed") or 0),
            calendar_upserted=int(sync_result.get("calendar_upserted") or 0),
            gmail_total=sync_result.get("gmail_total"),
            meetings_total=sync_result.get("meetings_total"),
            triaged=int(triaged["triaged"]),
            pending=int(triaged["pending"]),
            run_id=triaged.get("run_id"),
            calendar_truncated=bool(sync_result.get("calendar_truncated") or False),
            gmail_truncated=bool(sync_result.get("gmail_truncated") or False),
        )
    except EncryptionUnavailableError as exc:
        raise safe_error(503, "encryption_unavailable", "Token encryption unavailable.") from exc
    except google_sync.GoogleReauthRequired as exc:
        raise safe_error(401, "google_reauth_required", "Google re-auth required.") from exc
    except GoogleHttpError as exc:
        import logging

        status = exc.status_code
        # Prefer specific upstream code (gmail_get_failed, gmail_history_failed, …).
        code = str(exc.args[0]) if exc.args else "google_sync_failed"
        if not code or code == "GoogleHttpError":
            code = "google_sync_failed"
        logging.getLogger("opspilot.api.oauth").error(
            "google_sync_failed request_id=%s error_code=%s upstream_status=%s",
            getattr(request.state, "request_id", None) or "-",
            code,
            status,
        )
        raise safe_error(
            502,
            code,
            "Google sync failed.",
            details={"upstream_status": status} if status is not None else None,
        ) from exc


@router.delete("/oauth/google", response_class=JSONResponse)
def disconnect_google(request: Request, session: Session = Depends(get_db_session)) -> JSONResponse:
    """Revoke Google token (best-effort), delete credential + cursors, clear cookie. Keeps synced data."""
    require_csrf_origin(request)
    if demo_mode_enabled():
        raise safe_error(403, "demo_mode_blocks_oauth", "DEMO_MODE blocks Google OAuth.")
    sess = verify_session(request.cookies.get(COOKIE_NAME))
    if sess is None:
        raise safe_error(401, "operator_auth_required", "Operator session required.")
    cred = oauth_credentials.get_decrypted_refresh(session, provider="google")
    if cred is not None:
        account_email, refresh = cred
        revoke_refresh_token(refresh)
        sync_cursors.delete_for_account(session, provider="google", account_email=account_email)
        oauth_credentials.delete_provider(session, provider="google", account_email=account_email)
    else:
        oauth_credentials.delete_provider(session, provider="google")

    response = JSONResponse({"status": "disconnected"})
    clear_operator_cookie(response)
    return response
