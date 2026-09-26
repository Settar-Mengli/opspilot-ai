# D-023: Anthropic Prepaid Usage Gate

- **Date:** 2026-09-26
- **Status:** Accepted
- **Blocks:** B2, B3, B7

## Context

Owner has prepaid Anthropic credits and wants teacher/demo quality without further spend and without making Claude the product default. Accidental pytest burns under .env are a CURRENT risk (V1).

## Options

| Option | Tradeoffs |
|--------|-----------|
| (a) Ban Anthropic entirely | Safest spend; loses teacher/demo quality |
| (b) Default to Anthropic until credits die | Violates zero-spend intent; burns prepaid |
| (c) Opt-in + hard token **and** USD budget in gateway | Controlled quality; CI stays free |

## Decision

**(c)** Anthropic opt-in only:
- OPSPILOT_ANTHROPIC_ENABLED default false
- Allowlisted tasks only (e.g. leaderboard, judge_calibration, demo_quality) — never visitor /ask (D2)
- Hard remaining budget in **tokens and USD** (debit from LlmCall)
- Forbidden in unit/API tests and CI
- Budget exhausted → fail closed to Gemini/Groq/Ollama

## Acceptance criteria

- B2 tests: disabled or budget=0 → no HTTP to Anthropic; allowlisted+budget mocked path allowed.
- B3: optional prepaid leaderboard column labeled prepaid/budgeted.
- B7: prod OPSPILOT_ANTHROPIC_ENABLED=false unless capped operator demo window; visitors cannot select Anthropic.

## Consequences

Demo/leaderboard can use Haiku/Sonnet-class quality sparingly; CI stays free.

## Blocks

B2, B3, B7.
