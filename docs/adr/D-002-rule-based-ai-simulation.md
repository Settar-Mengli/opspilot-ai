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

## Consequences

Higher determinism and easier testing; lower semantic flexibility early. Remains the CI/default fallback under the TARGET gateway.
