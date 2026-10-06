# Anthropic operator switch pre-audit — 2026-10-05

Ask/Plan evidence against `main` @ `3bc7753` (PR #46). Claims below are **CURRENT** only where verified in code; planned behaviour is **TARGET** (b6.1).

## Verdict table

| ID | Claim | Verdict | Evidence |
|----|--------|---------|----------|
| P1 | Anthropic stripped from `provider_order` / `build_providers` | CONFIRMED | `routing.py:20–26`, `29–67` |
| P2 | D-023 gate allowlists `demo_quality` / `leaderboard` / `judge_calibration` only; never `ask`/`triage` | CONFIRMED | `anthropic.py:17`, `62–63`, `66–89` |
| P3 | Env budget seed + post-success debit (no pre-call reserve) | CONFIRMED | `anthropic_budget.py:22–94`; `gateway.py:275–279` |
| P4 | No Anthropic CLI job module | CONFIRMED | no `jobs/anthropic_budget.py` on tip |
| P5 | Startup logs `ANTHROPIC_ENABLED`; no `ANTHROPIC_LEDGER`; no ENABLED∧DEMO refuse | CONFIRMED | `startup_config.py:58–70`; `app.py:131–134` |
| P6 | Operator session verify: BadSignature/expired/wrong role → None; role must be `demo_operator` | CONFIRMED | `operator_session.py:41–63` |
| P7 | Ask SSE / Sync drain have no operator Anthropic auth wiring | CONFIRMED | `routes_ask.py`; `oauth_routes.py` spawn; `drain.py` |
| P8 | Morning preflight refuses when `anthropic_enabled()` | CONFIRMED | `morning_run.py:37–42` (`_preflight`) |
| P9 | Alembic head `0010` includes `anthropic_prepaid_budget` | CONFIRMED | `alembic/versions/` head 0010 |
| P10 | AttemptStatus has no reservation-specific enum; includes `error` | CONFIRMED | `types.py:27–32` |
| P11 | Rates / model verify-at-decision-time; default model haiku id in code | CONFIRMED | `anthropic.py:108`; ADR D-023 addenda |
| P12 | PART 19 item 1 TARGET: operator Ask+triage, off by default, hard cap | CONFIRMED | `OPSPILOT-MASTER-RECORD.md` PART 19 |

## Gaps closed by b6.1 (TARGET)

| Gap | Work |
|-----|------|
| Ask/triage never allowlisted; stripped from routing | Operator auth + prepend when authorized |
| No pre-call reservation | Atomic reserve + LlmCall open row; reconcile |
| Env BUDGET_* seed / gate | CLI sole writer; remove seed |
| No CLI show counts | `jobs.anthropic_budget show/set` |
| ENABLED∧DEMO can co-exist | Startup refuse |
| No request-scoped auth | `OperatorAnthropicAuth.from_session` only from Ask/Sync routes |

## Non-goals (confirmed)

- Migration / new AttemptStatus value
- Visitor Ask Anthropic; morning job Anthropic; FE / PNG / workflow diffs
- C9 PART 20 / ADR CURRENT flips before owner LIVE
- Paid API purchase; printing secrets; editing `.env`
