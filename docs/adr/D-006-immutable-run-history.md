# D-006: Immutable Run History With Latest Compatibility

- **Date:** 2026-05-29
- **Status:** Accepted
- **Blocks:** B1

## Context

Need run-to-run traceability while preserving latest-output consumers.

## Decision

Keep writing latest artifacts to data/output/ and additionally write immutable per-run artifacts to data/history/runs/....

## Alternatives considered

Replace latest outputs entirely; add a database before proving local history value.

## Consequences

CURRENT file history remains until B1 Postgres migration; TARGET persists runs/items in Neon while retaining export/demo paths as needed.
