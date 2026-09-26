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

## Consequences

Complementary portfolio story; quota burn risk — gate with metering and evals (B3 before/with tools on real bodies).
