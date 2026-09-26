# D-010: Async HTTP, sync database

- **Date:** 2026-09-26
- **Status:** Accepted (revised B1 fix pass)
- **Blocks:** B1, B2, B5
- **Owner ruling:** O1 (B1 fix pass)

## Context

B5 SSE Ask and B2 multi-provider HTTP need non-blocking request handlers. Windows uvicorn defaults to Proactor, which breaks `psycopg` async drivers. Split stacks (async tests + sync API) reduced test fidelity.

## Decision

- **Database:** All DB access uses **sync** SQLAlchemy 2 + `psycopg` (API handlers, X5 importer, pipeline persistence, pytest fixtures). No async engines/sessions in-tree.
- **HTTP:** Prefer async FastAPI route handlers where I/O-bound outbound HTTP or SSE is required (B2 gateway, B5 SSE). Sync route handlers remain valid for pure DB/CPU work (FastAPI runs them in a threadpool).
- Async is **not** used for ORM/session lifecycle.

## Alternatives considered

(a) Async ORM everywhere + WindowsSelectorEventLoopPolicy — rejected for B1 (Proactor/--reload footguns; dual stacks).
(b) Sync-only app forever — rejected; B5 SSE needs async generators.

## Acceptance criteria

- B1: single sync Session path; Windows live smoke POST/GET runs without event-loop policy hacks.
- B5: SSE Ask does not block the event loop; DB calls stay sync (threadpool or short critical sections).

## Consequences

Delete async DB helpers and `import_json_sync` dual path. Revise PART 3 Q4 to sync DB. Provider SDKs remain outside this ADR (D-024 / B2).
