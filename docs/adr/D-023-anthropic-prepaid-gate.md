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

## Addendum (B2, 2026-09-29)

Env (fail closed when enabled without rates):

| Var | Role |
|-----|------|
| `OPSPILOT_ANTHROPIC_ENABLED` | default false |
| `OPSPILOT_ANTHROPIC_BUDGET_TOKENS` | remaining token budget |
| `OPSPILOT_ANTHROPIC_BUDGET_USD` | remaining USD budget |
| `OPSPILOT_ANTHROPIC_USD_PER_MTOK_IN` / `_OUT` | **required when enabled**; debit from SDK `usage` |

Allowlist tasks: `demo_quality`, `leaderboard`, `judge_calibration` — **never** `ask`. Rates **VERIFY AT DECISION TIME** against Anthropic pricing before enabling.

## Addendum (B3, 2026-09-30)

- B3 leaderboard Anthropic column is documented as **`skipped`** (lock P7). **No Anthropic HTTP** in B3; zero-spend. Optional prepaid column remains future (D-018 historical AC superseded for B3 by P7).

## Addendum (b6.1 operator switch, 2026-10-05) — TARGET until C9

Status of this addendum: **TARGET** (not CURRENT). CURRENT flips happen only in C9 after owner LIVE. Until then, B2/B3 addenda above remain the runtime contract on `main`.

**Scope (TARGET):** Operator-authorized Anthropic for **Ask SSE** and **Sync drain triage** only. Off by default. Never visitors. Never morning job. Never tests/CI live calls.

**Auth (TARGET):** Request-scoped `OperatorAnthropicAuth` minted only via `from_session` from Ask and Sync routes after `verify_session` returns a `demo_operator` session. Soft-skip Anthropic (free path serves) when auth absent.

**Gate order (TARGET):** operator_auth → ENABLED → DEMO off → task in `{ask, triage}` → model allowlist → positive USD rates → `est_input` ≤ 16384 → SDK client constructible (`max_retries=0`, timeout default 25s) → ledger row exists → atomic reserve.

**Ledger (TARGET):** `anthropic_prepaid_budget` id=1 is SoT. CLI `show`/`set` sole writer (no env seed). Pre-call reserve + LlmCall open row (`status=error`, `error_code=anthropic_reserved`); reconcile refunds/keeps/excess in one transaction. Rates: env `OPSPILOT_ANTHROPIC_USD_PER_MTOK_IN`/`_OUT` (VERIFY AT DECISION TIME; plan baseline $1/$5 MTok). Default model `claude-haiku-4-5-20251001`.

**Startup (TARGET):** `OPSPILOT_ANTHROPIC_ENABLED` ∧ `OPSPILOT_DEMO_MODE` → refuse to start. Startup config prints `ANTHROPIC_LEDGER=1` when ledger row present.

**B7 note (TARGET):** Public host never has `ANTHROPIC_API_KEY` or enable flag.

**Supersedes (when CURRENT):** B2 addendum allowlist that excludes `ask`; env `OPSPILOT_ANTHROPIC_BUDGET_TOKENS`/`_USD` as runtime gate/seed.
