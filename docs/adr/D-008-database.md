# D-008: Database = Neon Postgres

- **Date:** 2026-09-26
- **Status:** Accepted
- **Blocks:** B1, B4, B7

## Context

File JSON persistence cannot support sync idempotency, preferences, LlmCall metering, or multi-host deploy. Free hosts have ephemeral disks — SQLite-on-disk is unsafe for public tiers.

## Options

| Option | Tradeoffs |
|--------|-----------|
| (a) Neon Postgres | Free tier; scale-to-zero; real SQL; CI can use Postgres service |
| (b) Turso/libSQL | Edge-friendly; different dialect; VERIFY free tier |
| (c) SQLite local + Postgres prod | Split-brain tests; ephemeral disk risk on free BE |
| (d) Stay on files | Blocks B4/B6 metering and sync |

## Decision

**(a)** Neon Postgres as system of record. CI uses a **real Postgres service** (no SQLite split brain). Local Postgres strategy (Docker Desktop vs Neon branch) is chosen in the **B1 plan**.

## Acceptance criteria

- B1: Alembic migrations apply on CI Postgres; app reads/writes WorkItems/Runs from Postgres in smoke.
- No production path uses SQLite.
- Free-tier Neon quotas labeled VERIFY AT DECISION TIME in B1/B7 plans.

## Consequences

Need SQLAlchemy/Alembic (D-009). Operator owns Neon project and connection strings as secrets.

## Blocks

B1, B4, B7.
