# D-010: Async FastAPI

- **Date:** 2026-09-26
- **Status:** Accepted
- **Blocks:** B1, B5

## Context

SSE streaming and concurrent provider I/O need non-blocking request handlers.

## Decision

Prefer async FastAPI routes and async DB/session patterns where I/O-bound. Sync bridge only at clear boundaries during migration.

## Alternatives considered

Stay fully sync; Starlette-only custom app.

## Consequences

Migrate carefully from CURRENT sync handlers; B5 SSE depends on this.
