"""OAuth + sync API routes (B4 → B6 C5: drain-based sync)."""

from __future__ import annotations

import contextvars
import logging
import os
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from opspilot.api.csrf import require_csrf_origin
from opspilot.api.deps import get_db_session
from opspilot.api.schemas import JobStatusResponse, SyncResponse, safe_error
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

logger = logging.getLogger("opspilot.api.oauth")

router = APIRouter(tags=["oauth"])

# Frozen at Sync start; copy_context() carries it into the drain thread.
# Keeps _spawn_sync_drain(job_id, generation, ceiling) arity stable for hermetic mocks (B6).
_sync_drain_operator_auth: contextvars.ContextVar[object | None] = contextvars.ContextVar(
    "opspilot_sync_drain_operator_auth", default=None
)

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
def post_sync(request: Request, session: Session = Depends(get_db_session)) -> JSONResponse:
    """Sync Google → Postgres, then drain triage in background.

    Returns 202 (started), 200 (not_needed), or 200 (busy).
    """
    # 1. DEMO → 403
    if demo_mode_enabled():
        raise safe_error(403, "demo_mode_blocks_sync", "DEMO_MODE blocks sync.")
    # 2. Cookie → 401
    sess = verify_session(request.cookies.get(COOKIE_NAME))
    if sess is None:
        raise safe_error(401, "operator_auth_required", "Operator session required.")
    # 3. CSRF → 403
    require_csrf_origin(request)

    from opspilot.persistence.repositories import work_items
    from opspilot.services.drain import sync_request_ceiling
    from opspilot.services.ops_jobs import claim_lease_idle, reap_stale_jobs

    try:
        # 4. google_sync.run_sync + commit
        sync_result = google_sync.run_sync(session)
        session.commit()
    except EncryptionUnavailableError as exc:
        raise safe_error(503, "encryption_unavailable", "Token encryption unavailable.") from exc
    except google_sync.GoogleReauthRequired as exc:
        raise safe_error(401, "google_reauth_required", "Google re-auth required.") from exc
    except GoogleHttpError as exc:
        status = exc.status_code
        code = str(exc.args[0]) if exc.args else "google_sync_failed"
        if not code or code == "GoogleHttpError":
            code = "google_sync_failed"
        logger.error(
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

    # Sync counts for the response.
    sc_email = str(sync_result.get("account_email") or "")
    sc_gmail_upserted = int(sync_result.get("gmail_upserted") or 0)
    sc_gmail_removed = int(sync_result.get("gmail_removed") or 0)
    sc_calendar_upserted = int(sync_result.get("calendar_upserted") or 0)
    _gmail_total_raw = sync_result.get("gmail_total")
    sc_gmail_total: int | None = int(_gmail_total_raw) if _gmail_total_raw is not None else None
    _meetings_total_raw = sync_result.get("meetings_total")
    sc_meetings_total: int | None = int(_meetings_total_raw) if _meetings_total_raw is not None else None
    sc_calendar_truncated = bool(sync_result.get("calendar_truncated") or False)
    sc_gmail_truncated = bool(sync_result.get("gmail_truncated") or False)

    def _sync_resp(drain: str, *, job_id: str | None = None, pending: int = 0) -> SyncResponse:
        return SyncResponse(
            drain=drain,
            job_id=job_id,
            account_email=sc_email,
            gmail_upserted=sc_gmail_upserted,
            gmail_removed=sc_gmail_removed,
            calendar_upserted=sc_calendar_upserted,
            gmail_total=sc_gmail_total,
            meetings_total=sc_meetings_total,
            calendar_truncated=sc_calendar_truncated,
            gmail_truncated=sc_gmail_truncated,
            pending=pending,
        )

    # 5. Reap stale jobs.
    reap_stale_jobs(session)
    session.commit()

    # 6. Count pending.
    pending = work_items.count_gmail_untriaged(session)

    if pending == 0:
        return JSONResponse(content=_sync_resp("not_needed").model_dump(), status_code=200)

    # Claim lease BEFORE INSERT in one txn; if no lease, do not INSERT.
    from datetime import UTC, date, datetime

    from sqlalchemy import text as sa_text

    from opspilot.persistence.repositories.ops_jobs import new_ops_job_id

    job_id = new_ops_job_id()
    ceiling = sync_request_ceiling()
    now = datetime.now(UTC)

    # Insert job row first (FK requirement for lease), then attempt lease claim.
    session.execute(
        sa_text(
            "INSERT INTO ops_jobs (id, job_kind, day_utc, status, force_override, "
            "created_at, request_ceiling, metadata_json) "
            "VALUES (:id, 'sync_drain', :day, 'queued', false, :now, :ceil, '{}'::jsonb)"
        ),
        {"id": job_id, "day": date.today(), "now": now, "ceil": ceiling},
    )
    session.flush()

    generation = claim_lease_idle(session, job_id)
    if generation is None:
        # Lease held — busy. Roll back so the queued job row is not persisted.
        session.rollback()
        pending = work_items.count_gmail_untriaged(session)
        return JSONResponse(content=_sync_resp("busy", pending=pending).model_dump(), status_code=200)

    session.commit()

    # Wake in-process drain worker (does not block the request).
    from opspilot.llm.operator_auth import OperatorAnthropicAuth

    cookie = request.cookies.get(COOKIE_NAME)
    _sync_drain_operator_auth.set(OperatorAnthropicAuth.from_session(verify_session(cookie)))
    _spawn_sync_drain(job_id, generation, ceiling)

    return JSONResponse(
        content=_sync_resp("started", job_id=job_id, pending=pending).model_dump(),
        status_code=202,
    )


def _spawn_sync_drain(job_id: str, generation: int, ceiling: int) -> None:
    """Fire-and-forget drain in a background thread (pipeline.py pattern)."""
    ctx = contextvars.copy_context()
    operator_auth = _sync_drain_operator_auth.get()

    def _run() -> None:
        from opspilot.persistence.db import create_engine, create_session_factory, get_database_url
        from opspilot.persistence.models import OpsJobRow
        from opspilot.persistence.repositories.ops_jobs import update_ops_job_fields
        from opspilot.services.drain import DrainResult, drain
        from opspilot.services.ops_jobs import release_lease

        engine = create_engine(get_database_url())
        factory = create_session_factory(engine)
        session = factory()
        try:
            job = session.get(OpsJobRow, job_id)
            if job is None:
                logger.error("sync_drain job_id=%s not found", job_id)
                return
            drain_result: DrainResult = drain(
                session,
                job=job,
                generation=generation,
                ceiling=ceiling,
                operator_auth=operator_auth,
            )
            final_status = "succeeded"
            if drain_result.ceiling_hit or drain_result.budget_exhausted:
                final_status = "partial"

            from datetime import UTC, datetime

            update_ops_job_fields(
                session,
                job,
                status=final_status,
                triaged=drain_result.triaged,
                pending=0,  # will be recounted
                request_count=drain_result.request_count,
                rules_fallback_count=drain_result.rules_fallback_count,
                ceiling_hit=drain_result.ceiling_hit,
                budget_exhausted=drain_result.budget_exhausted,
                run_id=drain_result.run_id,
                finished_at=datetime.now(UTC),
            )
            from opspilot.persistence.repositories import work_items

            final_pending = work_items.count_gmail_untriaged(session)
            update_ops_job_fields(session, job, pending=final_pending)
            release_lease(session, job_id, generation)
            session.commit()
            logger.info(
                "sync_drain completed job=%s status=%s triaged=%s pending=%s",
                job_id,
                final_status,
                drain_result.triaged,
                final_pending,
            )
        except Exception:
            logger.exception("sync_drain failed job=%s", job_id)
            try:
                session.rollback()
                job = session.get(OpsJobRow, job_id)
                if job is not None:
                    from datetime import UTC, datetime

                    update_ops_job_fields(
                        session,
                        job,
                        status="failed",
                        error_code="sync_drain_error",
                        finished_at=datetime.now(UTC),
                    )
                    release_lease(session, job_id, generation)
                    session.commit()
            except Exception:
                logger.exception("sync_drain cleanup failed job=%s", job_id)
        finally:
            session.close()
            engine.dispose()

    executor = ThreadPoolExecutor(max_workers=1)
    executor.submit(ctx.run, _run)
    executor.shutdown(wait=False)


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(
    job_id: str,
    request: Request,
    session: Session = Depends(get_db_session),
) -> JobStatusResponse:
    """Return job status fields. Cookie required."""
    sess = verify_session(request.cookies.get(COOKIE_NAME))
    if sess is None:
        raise safe_error(401, "operator_auth_required", "Operator session required.")

    from opspilot.persistence.repositories.ops_jobs import get_ops_job

    job = get_ops_job(session, job_id)
    if job is None:
        raise safe_error(404, "job_not_found", "Job not found.")

    return JobStatusResponse(
        id=job.id,
        job_kind=job.job_kind,
        status=job.status,
        triaged=job.triaged,
        pending=job.pending,
        error_code=job.error_code,
        run_id=job.run_id,
        created_at=job.created_at.isoformat(),
        started_at=job.started_at.isoformat() if job.started_at else None,
        finished_at=job.finished_at.isoformat() if job.finished_at else None,
    )


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
