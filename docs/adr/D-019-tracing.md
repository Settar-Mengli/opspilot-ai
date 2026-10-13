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
- **Error meta (S1):** non-2xx → `meta.status_code` + redacted `provider_error` (≤500 chars, F-09). Parse/validation failure → `error_class`, redacted `validation_error`, `output_len`, redacted `output_head` (≤300). Schema/format 400 → optional `force_json_object` retry attempt is a **separate** `LlmCall` row.

## Addendum (public-log hardening, 2026-10-12)

- When `CI=true`, `append_llm_jsonl` skips disk and does **not** re-call `emit_llm_span` (gateway already emitted — no double emit).
- When `GITHUB_ACTIONS=true`, `emit_llm_span` strips free-text meta keys `provider_error`, `output_head`, `validation_error` from the log payload; keeps `status_code`, `error_class`, `output_len`. DB `llm_calls.meta` is unchanged.
