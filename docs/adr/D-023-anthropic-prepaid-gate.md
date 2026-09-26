# D-023: Anthropic Prepaid Usage Gate

- **Date:** 2026-09-26
- **Status:** Accepted
- **Blocks:** B2, B3, B7

## Context

Owner has prepaid Anthropic credits and wants teacher/demo quality without further spend and without making Claude the product default. Accidental pytest burns under .env are a CURRENT risk (V1).

## Decision

Option (c): Anthropic is **opt-in only** behind gateway checks:
- OPSPILOT_ANTHROPIC_ENABLED default false
- Allowlisted tasks only (e.g. leaderboard, judge_calibration, demo_quality) — never visitor /ask
- Hard remaining budget in **tokens and USD** (debit from LlmCall usage)
- Forbidden in unit/API tests and CI (fakes assert client never constructed)
- When budget exhausted → fail closed to Gemini/Groq/Ollama

## Alternatives considered

(a) Ban Anthropic entirely; (b) Default to Anthropic until credits die.

## Consequences

Demo/leaderboard can use Haiku/Sonnet-class quality sparingly; CI stays free; B2 exit criteria include budget gate tests; B7 prod keeps Anthropic disabled unless operator opens a capped demo window.
