# D-003: CLI-First Vertical Slice

- **Date:** 2026-05-29
- **Status:** Accepted
- **Blocks:** —

## Context

Need delivery signal quickly without UI overhead.

## Decision

Prioritize a runnable CLI workflow before any frontend work.

## Alternatives considered

Dashboard-first implementation.

## Options

| Option | Tradeoffs |
|--------|-----------|
| (a) CLI first | Fast signal; UI deferred |
| (b) Dashboard first | Slower vertical slice |

## Acceptance criteria

- CLI remains runnable; B1 moves API \/run\ to in-process (no fragile subprocess-only path).

## Consequences

Faster value delivery; UI deferred. CLI remains a local operator path; API should call pipeline in-process (see V3 / B1).
