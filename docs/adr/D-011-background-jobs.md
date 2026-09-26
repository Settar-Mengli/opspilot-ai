# D-011: Background Via In-Process + GHA Cron (No Celery)

- **Date:** 2026-09-26
- **Status:** Accepted
- **Blocks:** B6

## Context

Morning brief and sync jobs need scheduling without paid worker infra. Celery/Redis duplicates the other portfolio stack.

## Decision

In-process jobs for request-scoped work; **GitHub Actions cron** calling an authenticated backend webhook for morning runs. No Celery/RQ.

## Alternatives considered

Celery + Redis; always-on worker on paid host; pure client-side timers.

## Consequences

Tolerate free-tier cold starts; secure cron with HMAC/shared secret (X2 in B6).
