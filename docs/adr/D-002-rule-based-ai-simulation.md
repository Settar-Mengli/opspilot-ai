# D-002: Rule-Based AI Simulation First

- **Date:** 2026-05-29
- **Status:** Accepted
- **Blocks:** —

## Context

No paid API keys and no external dependencies in early milestones.

## Decision

Implement deterministic rule-based triage before model-backed approaches.

## Alternatives considered

Immediate LLM integration; hybrid model from day one.

## Options

| Option | Tradeoffs |
|--------|-----------|
| (a) Rules first | Deterministic CI; lower early flexibility |
| (b) LLM from day one | Spend risk; flaky tests |

## Acceptance criteria

- Rule-based triage remains a CI/default fallback under the TARGET gateway.

## Consequences

Higher determinism and easier testing; lower semantic flexibility early. Remains the CI/default fallback under the TARGET gateway.
