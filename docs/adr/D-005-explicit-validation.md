# D-005: Explicit Validation And Error Boundaries

- **Date:** 2026-05-29
- **Status:** Accepted
- **Blocks:** —

## Context

Schema checks and failures were too implicit for predictable CLI UX.

## Decision

Add explicit input schema validation, structured pipeline logging, and user-facing exception boundaries in loader, pipeline, and CLI layers.

## Alternatives considered

Keep raw exceptions and rely only on test coverage.

## Consequences

Better debuggability and cleaner failures for local runs.
