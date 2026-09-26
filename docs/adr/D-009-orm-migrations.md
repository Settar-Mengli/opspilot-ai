# D-009: SQLAlchemy 2 + Alembic; Postgres in Tests

- **Date:** 2026-09-26
- **Status:** Accepted
- **Blocks:** B1

## Context

Need typed models and reproducible schema for Neon.

## Decision

SQLAlchemy 2.x + Alembic migrations. Tests run against Postgres (service container or equivalent), not a separate SQLite dialect.

## Alternatives considered

Raw SQL only; Django ORM; SQLite for unit tests.

## Consequences

Slightly heavier local/CI setup; one schema truth. Aligns with D-008.
