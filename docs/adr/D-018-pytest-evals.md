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

## Options

| Option | Tradeoffs |
|--------|-----------|
| (a) Custom pytest CORE | Free; hermetic CI lane |
| (b) Paid eval SaaS | Cost; less control |

## Acceptance criteria

- B3: deterministic CI lane + red-team on same harness; optional prepaid Anthropic column.

## Consequences

B3 is a hard gate before trusting tool-using Ask on email bodies.

## Addendum (B3, 2026-09-30)

- Lock **P7** wins over the Acceptance Criteria “optional prepaid Anthropic column”: B3 publishes Anthropic as **`skipped`** with **no Anthropic HTTP**. See D-028 / D-023 B3 addendum. Harness details: D-028; defenses + ASR: D-029.
