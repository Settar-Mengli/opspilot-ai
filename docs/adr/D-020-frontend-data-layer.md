# D-020: Fetch + Hooks; TanStack Later If Needed

- **Date:** 2026-09-26
- **Status:** Accepted
- **Blocks:** B5

## Context

CURRENT client is thin fetch wrappers. SSE Ask and approval flows need clarity without a premature cache framework.

## Decision

Keep fetch + React hooks. Introduce TanStack Query only if caching/invalidation complexity forces it.

## Alternatives considered

TanStack now; tRPC; GraphQL.

## Options

| Option | Tradeoffs |
|--------|-----------|
| (a) Fetch + hooks | Minimal |
| (b) TanStack now | Premature cache complexity |

## Acceptance criteria

- B5 SSE works with fetch/hooks; TanStack only if invalidation pain appears.

## Consequences

Less FE churn in B0–B5; revisit post-SSE.
