# D-019: OTel-Compatible + LlmCall/JSONL; Phoenix UI Deferred

- **Date:** 2026-09-26
- **Status:** Accepted
- **Blocks:** B2

## Context

No timeouts/retries/telemetry on LLM calls (AI-03). Need metering for free tiers and Anthropic budget.

## Decision

Ship **LlmCall** persistence + JSONL/OTel-compatible hooks in B2 with the gateway. Phoenix (or similar) UI is deferred until hooks prove useful.

## Alternatives considered

LangSmith; Phoenix from day one; logs only.

## Consequences

Budget gate and leaderboard can debit real usage; CI asserts no live Anthropic.
