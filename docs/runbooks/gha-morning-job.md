# GHA morning job (B6) runbook

## Purpose

Run the OpsPilot morning triage/brief **inside a GitHub Actions runner** (D-011). Writes results to Neon and notifies Telegram. **No public backend** is required before B7.

## Prerequisites

- Neon database at expected Alembic head (operator applied migrations; cron never migrates).
- GHA secrets: Gemini and/or Groq API keys, `DATABASE_URL` (Neon), Telegram bot token, **token-encryption key**.
- Encrypted Google refresh token already stored in Neon (see [google-oauth-reauth.md](google-oauth-reauth.md)).

## Behavior

1. Install package in the runner.
2. Fail fast if Neon schema revision ≠ expected Alembic head.
3. Decrypt refresh token from Neon; on auth failure → skip sync, brief from existing data, Telegram “re-auth needed”.
4. Sync (if auth OK) → triage/brief → persist Run + outputs → Telegram notify.

## VERIFY AT DECISION TIME

| Item | Note |
|------|------|
| (a) Schedule disable | GitHub may disable scheduled workflows on public repos after ~60 days without repository activity — job must be **re-enable-aware**; document how to re-enable |
| (b) Cron timing | Schedules are UTC and can be delayed |
| (c) Minutes/limits | Actions minutes and concurrency for public repos change — verify before relying on frequent runs |

## Operator checklist

- [ ] Secrets present in repo Settings → Secrets
- [ ] Neon migration head matches app expectation
- [ ] Weekly OAuth re-auth current
- [ ] After ~60 days idle: confirm workflow still enabled
