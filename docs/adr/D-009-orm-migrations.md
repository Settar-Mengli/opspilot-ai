# D-009: SQLAlchemy 2 + Alembic; Postgres in Tests

- **Date:** 2026-09-26
- **Status:** Accepted
- **Blocks:** B1

## Context

Need typed models and reproducible schema for Neon (D-008).

## Options

| Option | Tradeoffs |
|--------|-----------|
| (a) SQLAlchemy 2 + Alembic on Postgres everywhere | One dialect; slightly heavier CI |
| (b) Raw SQL only | Faster start; weaker models/migrations |
| (c) SQLite for unit tests | Split dialect; false greens |

## Decision

**(a)** SQLAlchemy 2.x + Alembic. Tests run against Postgres (service container or equivalent).

## Acceptance criteria

- B1 exit: Alembic upgrade → downgrade → upgrade round-trip on CI Postgres.
- Domain models live under TARGET persistence/ / domain/ (D-024).
- Cron never runs migrations (D-011).

## Consequences

CI must provision Postgres. Local-dev runbook documents connection setup.

## Blocks

B1.
