# D-018: Custom Pytest Evals CORE

- **Date:** 2026-09-26
- **Status:** Accepted
- **Blocks:** B3

## Context

No eval harness today (AI-04). Portfolio needs deterministic + optional hosted lanes without paid eval SaaS.

## Decision

Custom pytest-based eval CORE: golden/synthetic cases, schema asserts, red-team cases on the **same harness** as injection (B3). Lanes: deterministic CI; optional Ollama; manual free hosted; optional prepaid Anthropic column (D-023).

## Alternatives considered

Promptfoo/LangSmith paid; defer evals until after agentic Ask.

## Consequences

B3 is a hard gate before trusting tool-using Ask on email bodies.
