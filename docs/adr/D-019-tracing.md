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

## Options

| Option | Tradeoffs |
|--------|-----------|
| (a) LlmCall + JSONL/OTel hooks first | Enough for budgets |
| (b) Phoenix UI day one | Extra ops |

## Acceptance criteria

- B2: every gateway call can persist LlmCall; Phoenix UI deferred.

## Consequences

Budget gate and leaderboard can debit real usage; CI asserts no live Anthropic.

## Addendum (B2, 2026-09-29)

- One `LlmCall` row per **provider attempt** (statuses: `success|error|429|timeout|budget_denied|policy_denied`).
- JSONL under `data/llm_traces/` (gitignored) or stdout-oriented logging when `CI=true`; disable with `OPSPILOT_LLM_JSONL=0`.
- OTel-compatible structured log attrs (`gen_ai.*` style) via `opspilot.obs.tracing`; Phoenix UI still deferred.
