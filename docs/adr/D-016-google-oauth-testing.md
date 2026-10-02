# D-016: Google OAuth Testing Forever; Operator-Only Gmail; Encrypted Refresh in Neon

- **Date:** 2026-09-26
- **Status:** Accepted
- **Blocks:** B4, B6, B7

## Context

Visitor Gmail connect risks verification/CASA and breaks zero-spend. Demo needs operator inbox/calendar only. Google OAuth **Testing** refresh tokens are commonly cited as expiring ~7 days after issue (**VERIFY AT DECISION TIME**).

## Options

| Option | Tradeoffs |
|--------|-----------|
| (a) Store refresh token as GHA secret | Simple; weekly update requires editing secrets; not app-driven |
| (b) Store encrypted refresh token in Neon; key from env/GHA; weekly local re-auth writes Neon | App-owned rotation; runner reads DB; needs encryption + re-auth runbook |
| (c) Publish OAuth app / long-lived production tokens | Verification cost; out of zero-spend portfolio scope |

## Decision

**(b)** + Testing forever + operator-only demo account; visitors never connect Gmail.

- Refresh token stored **encrypted in Neon**; encryption key from env / GHA secrets — **not** the raw token as a GHA secret.
- Operator re-auths **weekly** via local app OAuth flow; app writes new ciphertext to Neon.
- B6 runner reads token from Neon, decrypts with key from secrets.
- On auth failure: morning job **fails closed** — skip sync, brief from existing data, Telegram alert “re-auth needed”.

## Acceptance criteria

- D-016, ROADMAP B4/B6, and `docs/runbooks/google-oauth-reauth.md` all state weekly re-auth + fail-closed behavior.
- No doc claims visitors can OAuth Gmail.
- Sync idempotency (X1) required in B4.
- The token is never logged or printed; the encryption scheme and key-rotation procedure are documented in `docs/runbooks/google-oauth-reauth.md`.

## Consequences

Operational burden: weekly re-auth. Brief may be stale if auth fails until operator fixes. Staying in Testing avoids CASA.

## Blocks

B4, B6, B7.

## Addendum (B4, 2026-09-30)

Implementation locks for B4:

- OAuth **authorization code + PKCE (S256)**; Google Cloud **Web** client.
- Redirect URI (exact): `http://127.0.0.1:8000/api/v1/oauth/google/callback`.
- Scopes: `openid`, `email`, `https://www.googleapis.com/auth/gmail.readonly`, `https://www.googleapis.com/auth/calendar.readonly` only.
- Refresh token Fernet-encrypted in Postgres `bytea`; env key `TOKEN_ENCRYPTION_KEY`.
- Operator session cookie: see D-030.
- Testing forever; weekly re-auth runbook remains SoT for rotation steps.

## Addendum (B4 STOP LIVE final, 2026-10-01)

- Required-scope gate: token response must include Gmail + Calendar readonly; never invent missing `scope`; incomplete grant → FE `oauth_error=grant_required`.
- `DELETE /api/v1/oauth/google` disconnect: best-effort revoke, delete credential + cursors, clear cookie; keep synced work_items/meetings.
- Sync commits before capped untriaged triage (`OPSPILOT_SYNC_TRIAGE_CAP`, default 10); Calendar `syncToken` requests omit window/`showDeleted=false`.
- Connected operator surfaces filter to `source_type=gmail` (G7); sample rows may remain in Neon but are not shown while connected.
- Live smoke on Neon verified (counts in PART 10); visitors never connect Gmail; DEMO_MODE blocks OAuth/sync.

## Addendum (B5, 2026-10-01) — gmail.send

- Add `https://www.googleapis.com/auth/gmail.send` to **SCOPES** and **REQUIRED_SCOPES** (required at Connect / token exchange). No `gmail.compose`.
- Operator must **Reconnect** (existing `prompt=consent` flow) to grant send; Testing mode forever unchanged.
- Send path remains HITL-only (D-033); DEMO_MODE continues to block OAuth/sync and **blocks approve/send**.

## Addendum (post-audit fix-pass, 2026-10-02) — truncation

- **Calendar:** on truncated incremental list, **clear** stored `syncToken` (do not keep prior). Next sync is full window with `showDeleted=true`. After a **complete** (non-truncated) full-window walk, absence-reconcile deletes local meetings whose `start_at` is in the same `[time_min, time_max)` window and whose `provider_id` was not returned. Truncated full window sets `calendar_truncated` and skips absence reconcile.
- **Gmail:** history truncate without a usable `last_hid` falls back to full list. If full list itself truncates, set `gmail_truncated`, keep prior cursor, do not claim a complete profile history id. Each sync remains bounded by max-pages env.
