# D-014: Hand-Rolled Bounded Agent Loop

- **Date:** 2026-09-26
- **Status:** Accepted
- **Blocks:** B5

## Context

Agentic Ask needs tools + multi-turn without cloning LangGraph HITL from the other portfolio repo.

## Decision

Hand-rolled loop with hard step cap (e.g. 4–6), read-only tools until approve&send, SSE for tokens/tool events. No LangGraph/CrewAI.

## Alternatives considered

LangGraph; crew frameworks; single-shot Ask only.

## Options

| Option | Tradeoffs |
|--------|-----------|
| (a) Hand-rolled bounded loop | Complementary portfolio; full control |
| (b) LangGraph | Overlap with other repo |
| (c) Single-shot Ask only | No tools |

## Acceptance criteria

- B5: step/time/token caps enforced; send requires approval; SSE events \	oken|tool_start|tool_end|final|error\.

## Consequences

Complementary portfolio story; quota burn risk — gate with metering and evals (B3 before/with tools on real bodies).
