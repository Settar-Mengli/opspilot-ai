# D-004: Adapter Seam For Future Models

- **Date:** 2026-05-29
- **Status:** Accepted
- **Blocks:** B2

## Context

Future model integrations are planned but should not destabilize core logic.

## Decision

Define provider adapter seam so pipeline orchestration stays provider-agnostic.

## Alternatives considered

Direct provider calls in orchestration logic.

## Options

| Option | Tradeoffs |
|--------|-----------|
| (a) Adapter seam | Swap providers; more design |
| (b) Direct SDK in orchestration | Faster now; couples core |

## Acceptance criteria

- B2: all LLM calls go through \llm/\ gateway; feature code does not import provider SDKs.

## Consequences

Better maintainability and swap capability. CURRENT: partial (conversation on AISettings; four adapters still hardcoded). TARGET: all calls through hand-rolled gateway (D-012).
