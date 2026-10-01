# D-030: Operator Session Cookie (Local Demo Auth)

- **Date:** 2026-09-30
- **Status:** Accepted
- **Blocks:** B4, B5, B6 (re-auth), B7 (extends)

## Context

B4 needs operator-only Google OAuth and sync without public rate limits (B7). The FE runs on `http://127.0.0.1:5173` and the API on `http://127.0.0.1:8000`, so the session cookie must work cross-origin with credentials (A1).

## Decision

- Cookie name: `opspilot_operator` (HTTP-only, `SameSite=Lax`, `Path=/`, `Secure=false` on local HTTP).
- Signed with `OPSPILOT_SESSION_SECRET` via itsdangerous `URLSafeTimedSerializer`.
- Payload: `{role: "demo_operator", email, exp}` (max-age 7 days — Testing refresh lifetime VERIFY AT DECISION TIME).
- Bootstrap: `GET /api/v1/oauth/google/start` allowed when `OPSPILOT_DEMO_MODE=0` without a cookie.
- Guarded: `POST /api/v1/sync` requires a valid operator cookie.
- CORS: `allow_credentials=True` with explicit allowlist origin `http://127.0.0.1:5173` (never `*`). Standardize on `127.0.0.1` for FE and API — not `localhost`.
- FE: API client uses `credentials: "include"`.

## Acceptance criteria

- Hermetic CORS preflight from allowed origin succeeds with credentials; other origins not echoed.
- DEMO_MODE blocks OAuth start and sync.
- Live smoke triggers sync via the Connections UI (not curl with a pasted cookie).

## Consequences

Local demo auth only; B7 must harden visitors/public exposure separately.

## Addendum (B4 STOP LIVE final, 2026-10-01)

- Live smoke confirmed Sync now via Connections UI with `credentials: "include"` (no pasted cookie).
- Guarded routes that require the operator cookie: `POST /api/v1/sync`, `DELETE /api/v1/oauth/google` (and DEMO_MODE blocks both).
- Disconnect clears the operator cookie; Reconnect re-enters PKCE start.
- B7 still owns public authn/authz (F-01), rate limits (F-02), and `/ready` (OBS-2).
