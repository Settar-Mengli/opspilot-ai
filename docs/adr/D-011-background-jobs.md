# D-011: Background Jobs — In-Process + GHA In-Runner Cron (No Celery)

- **Date:** 2026-09-26
- **Status:** Accepted
- **Blocks:** B6 (morning job), B7 (optional HMAC manual trigger only)

## Context

Morning brief and sync need scheduling without paid workers or a public backend before B7 (D6). Celery/Redis duplicates the other portfolio stack. Webhook-to-public-BE would violate D6.

## Options

| Option | Tradeoffs |
|--------|-----------|
| (a) GHA cron → HMAC webhook on public BE | Early prod-like wake; **requires public BE before B7** — violates D6 |
| (b) In-runner GHA job: install package, use secrets, write Neon, Telegram | Honors D6; secrets in GHA; no public bind; cold-start N/A |
| (c) Local Task Scheduler only | No GHA secrets; weak portfolio signal |

## Decision

**(b)** For B6: GitHub Actions cron runs the morning job **inside the runner**. Job installs the package; uses GHA secrets for Gemini/Groq keys, Neon URL, Telegram token, and **token-encryption key**; reads Google refresh token **from Neon** (encrypted); writes results to Neon; notifies Telegram. **No public backend** before B7.

X2 HMAC authenticated webhook is **B7-only**, optional manual/ops trigger to the deployed API — not required for B6 exit.

## Acceptance criteria

- B6 workflow YAML documents: schedule (UTC), required secrets, Neon access, fail-closed auth path.
- No B6 docs/ADR text require a publicly reachable backend.
- B7 may add optional HMAC `POST /api/v1/jobs/morning`; B6 exit does not depend on it.
- Runbook documents VERIFY AT DECISION TIME: (a) GHA may disable scheduled workflows on public repos after ~60 days without activity — re-enable-aware; (b) cron is UTC and can delay; (c) Actions minutes/limits for public repos.
- The job fails fast with a clear error if the Neon schema revision ≠ the expected Alembic head; migrations are applied by the operator, never by the cron job.

## Consequences

Portfolio “scheduled ops” without early public exposure. Operator must keep repo active or re-enable schedules. Encryption key never committed. Operator owns Alembic upgrades outside cron.

## Blocks

B6, B7 (X2 optional).
