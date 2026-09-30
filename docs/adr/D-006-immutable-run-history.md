# D-006: Immutable Run History With Latest Compatibility

- **Date:** 2026-05-29
- **Status:** Superseded by [D-025](D-025-run-history-postgres.md)
- **Blocks:** B1 (historical)

## Context

Need run-to-run traceability while preserving latest-output consumers.

## Decision

Keep writing latest artifacts to data/output/ and additionally write immutable per-run artifacts to data/history/runs/....

## Alternatives considered

Replace latest outputs entirely; add a database before proving local history value.

## Options

| Option | Tradeoffs |
|--------|-----------|
| (a) Latest + immutable history dirs | Auditability; disk growth |
| (b) Latest only | Simpler; no audit trail |
| (c) DB from day one | Was premature historically; now B1 |

## Acceptance criteria

- B1: Runs persisted in Postgres while preserving export/demo paths as needed.

## Consequences

CURRENT file history remains until B1 Postgres migration; TARGET persists runs/items in Neon while retaining export/demo paths as needed.

## Addendum (B3, 2026-09-30)

**Superseded by D-025.** API run history SoT is Postgres (no file primacy for `/api/v1` runs). This ADR is retained for history; do not implement file-based API history from D-006.
