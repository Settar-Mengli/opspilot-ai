# GHA morning job (D-011)

In-runner morning triage on GitHub Actions. **Not** triggered on push/PR. Schedule cron is present after owner `LIVE PASS` (C14); it runs only from the **default branch**.

## Workflow

[`.github/workflows/morning.yml`](../../.github/workflows/morning.yml)

- `schedule`: `0 12 * * *` (12:00 UTC = 07:00 America/Toronto standard; 08:00 during EDT)
- `workflow_dispatch` inputs: `force_override`, `simulate_google_reauth`
- Concurrency group `morning-run`, `cancel-in-progress: false`, timeout 30m
- `permissions: contents: read`
- Maps GitHub secrets → process env (see plan §11 / secrets table below)
- **Schedule on default branch:** C14 cron is on `main` (B6 merge PR #44 → `eae1a9a`). Workflow state **active**. First `event=schedule` run on `main` was **pending** at PART 18 closeout; until observed, use `workflow_dispatch` for manual runs. Branch-only pushes do not register cron.

## Secrets (names only)

| GitHub secret | Process env |
|---------------|-------------|
| `OPSPILOT_DATABASE_URL` | `DATABASE_URL` |
| `TOKEN_ENCRYPTION_KEY` | `TOKEN_ENCRYPTION_KEY` |
| `GOOGLE_OAUTH_CLIENT_ID` | `GOOGLE_OAUTH_CLIENT_ID` |
| `GOOGLE_OAUTH_CLIENT_SECRET` | `GOOGLE_OAUTH_CLIENT_SECRET` |
| `GEMINI_API_KEY` | `GEMINI_API_KEY` |
| `GROQ_API_KEY` | `GROQ_API_KEY` |
| `MISTRAL_API_KEY` | `MISTRAL_API_KEY` |
| `OPENROUTER_API_KEY` | `OPENROUTER_API_KEY` |
| `CLOUDFLARE_API_TOKEN` | `CLOUDFLARE_API_TOKEN` |
| `CLOUDFLARE_ACCOUNT_ID` | `CLOUDFLARE_ACCOUNT_ID` |
| `TELEGRAM_BOT_TOKEN` | `TELEGRAM_BOT_TOKEN` |
| `TELEGRAM_CHAT_ID` | `TELEGRAM_CHAT_ID` |

No `OPSPILOT_SESSION_SECRET` on this job.

## Operator steps

1. Confirm Neon Alembic head `0010_ops_jobs_corrections_budget`.
2. Actions → **Morning Run** → Run workflow.
3. Expect: job conclusion success/partial; Telegram counts-only message; `ops_jobs` status (counts only in chat/logs).
4. Auth-fail drill: `simulate_google_reauth=true` — sets `OPSPILOT_SIMULATE_GOOGLE_REAUTH=1` for that run only; does not modify credentials. Restore with default `false`.

## Telegram

Counts, flags, error codes only — never titles, subjects, bodies, links, or briefings.

`gmail_upserted` counts **updates and inserts** (not inserts-only). Rename deferred.

## Cron (C14 — after LIVE PASS)

`0 12 * * *` (= 07:00 America/Toronto standard; 08:00 during EDT). Present on default branch `main` after B6 merge (PR #44). First scheduled fire is the next 12:00 UTC after that merge (GHA may delay registration briefly). At PART 18 closeout, no `event=schedule` run on `main` had been observed yet.
