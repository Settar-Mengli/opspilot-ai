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
