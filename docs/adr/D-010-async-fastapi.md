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

## Options

| Option | Tradeoffs |
|--------|-----------|
| (a) Async FastAPI | SSE + concurrent I/O |
| (b) Sync-only | Simpler; blocks on LLM I/O |

## Acceptance criteria

- B5 SSE Ask works without blocking the event loop; B1 may migrate routes progressively.

## Consequences

Migrate carefully from CURRENT sync handlers; B5 SSE depends on this.

**B1 note:** FastAPI `/api/v1` DB handlers use sync `Session` so Windows uvicorn (Proactor) works with `psycopg`. Async SQLAlchemy remains for the CLI importer and truncate-managed pytest sessions. Treat the API sync path as the D-010 “sync bridge” until B5 SSE forces a Selector/async revisit.
