# D-008: Database = Neon Postgres

- **Date:** 2026-09-26
- **Status:** Accepted
- **Blocks:** B1, B4, B7

## Context

File JSON persistence cannot support sync idempotency, preferences, LlmCall metering, or multi-host deploy. Free hosts have ephemeral disks — SQLite-on-disk is unsafe for public tiers.

## Decision

Use **Neon Postgres** as the system of record. CI uses a **real Postgres service** (no SQLite split brain).

## Alternatives considered

Turso/libSQL; SQLite local + Postgres prod; stay on files.

## Consequences

Need SQLAlchemy/Alembic (D-009). Local Postgres strategy (Docker Desktop vs Neon branch) is **deferred to the B1 plan**. Free-tier Neon quotas = VERIFY AT DECISION TIME.
