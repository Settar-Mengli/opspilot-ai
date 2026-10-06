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

## Addendum (b6.1 operator switch, 2026-10-05) — CURRENT (shipped + LIVE)

Status of this addendum: **CURRENT** for clauses below that shipped on `b6.1/anthropic-operator` tip `e181818` and were proven in owner STOP LIVE 2026-10-05 (PART 20). **Anthropic remains off by default and is never reachable by visitors.** Unproven / future items stay labelled **TARGET**.

**Scope (CURRENT):** Operator-authorized Anthropic for **Ask SSE** and **Sync drain triage** only. Off by default. Never visitors. Never morning job. Never tests/CI live calls.

**Auth (CURRENT):** Request-scoped `OperatorAnthropicAuth` minted only via `from_session` from Ask and Sync routes after `verify_session` returns a real `OperatorSession` with role `demo_operator`. Soft-skip Anthropic (free path serves) when auth absent. Duck-typed role carriers are rejected.

**Gate order (CURRENT):** operator_auth → ENABLED → DEMO off → task in `{ask, triage}` → model allowlist → positive USD rates → `est_input` ≤ 16384 → SDK client constructible (`max_retries=0`, timeout default 25s) → ledger row exists → atomic reserve. Routing prepends Anthropic only when ENABLED + auth + allowlisted task.

**Ledger (CURRENT):** `anthropic_prepaid_budget` id=1 is SoT. CLI `show`/`set` is the **only** ledger writer (no env seed; retired `OPSPILOT_ANTHROPIC_BUDGET_TOKENS` / `_USD` not runtime). Pre-call reserve + LlmCall open row (`status=error`, `error_code=anthropic_reserved`); reconcile refunds/keeps/excess in one transaction. Rates: env `OPSPILOT_ANTHROPIC_USD_PER_MTOK_IN`/`_OUT` (platform.claude.com 2026-10-05: $1 / $5 MTok). Default model `claude-haiku-4-5-20251001`.

**Reservation / reconcile ownership (CURRENT, F1):** The Anthropic reserve path owns both the ledger debit and the single `llm_calls` row for that attempt. `session_attempt_recorder` never debits the Anthropic ledger and inserts no second Anthropic row when the attempt carries a reservation (`meta.ledger_row_owned`). Pre-reserve denials (no reservation) may still be recorded once by the recorder.

**Refund / keep (CURRENT):** `APIConnectionError` full refund only when `__cause__` is `httpx2.ConnectError`; other connection causes / missing cause → keep; HTTP 4xx → refund; HTTP 5xx / timeout / unclassified → keep.

**Startup (CURRENT):** `OPSPILOT_ANTHROPIC_ENABLED` ∧ `OPSPILOT_DEMO_MODE` → refuse to start. Startup config prints `ANTHROPIC_LEDGER=1` when ledger row present. Morning `_preflight` refuses when enabled.

**Standing ops rule (CURRENT, PART 21):** Never set `OPSPILOT_ANTHROPIC_ENABLED` or place `ANTHROPIC_API_KEY` outside the operator's local process. No public host planned (B7 backlog).

**Locks L1–L12 (CURRENT where implemented; L4 standing ops rule CURRENT (PART 21)):**

- **L1 Scope.** Anthropic may serve exactly two paths: (1) POST `/api/v1/ask/stream` (agent loop), (2) triage in the drain started by an operator POST `/api/v1/sync`. Nothing else: not legacy POST `/ask`, not POST `/runs`, not evening, insights, briefing, morning_run, evals, smoke scripts.
- **L2 Gate, fail-closed, ALL required per call:** `OPSPILOT_ANTHROPIC_ENABLED` true; `OPSPILOT_DEMO_MODE` off; a valid operator session cookie verified server-side on the originating request; task in `{ask, triage}`; model in an explicit allowlist; both USD rates set; ledger row exists and covers the reservation; `ANTHROPIC_API_KEY` present. Any failure → Anthropic is skipped and the existing free-tier order serves the request.
- **L3 Authorization is explicit, not ambient.** The route builds an authorization value from the verified cookie and passes it down to the gateway call. The Sync drain receives it explicitly from the Sync request that started it (parameter closure; no ContextVar). Any drain or job started another way never has it. No module-level or process-level "operator" flag.
- **L4 Standing ops / no shared host.** Startup refuses ENABLED∧DEMO. Never enable Anthropic or place the key outside the operator's local process (PART 21). If B7 is revived, that host must also lack key+flag. Non-operator sessions must never satisfy L2.
- **L5 Hard cap.** The `anthropic_prepaid_budget` ledger is the single source of truth. Before HTTP: atomic conditional reservation of worst case. After HTTP: reconcile to actual usage. Unknown outcome (timeout, transport error after send, cancel): keep the full reservation. No implicit seeding from env. Ledger set only by explicit operator CLI (`show` / `set`) that prints the database host label first and never prints secrets. No row → deny. Concurrency: two parallel calls cannot both pass on a ledger that covers one. Anthropic SDK client: `max_retries=0` and an explicit timeout. Every attempt is reserved, gets its own LlmCall row with `usd_estimate`, and counts toward `OPSPILOT_ASK_MAX_PROVIDER_CALLS`.
- **L6 Routing.** For an authorized ask/triage call Anthropic is tried first; on deny, exhaustion or error the existing order continues. Anthropic never appears in the default order string. Handle the daily-counter map (`budgets.py`) for anthropic explicitly WITHOUT weakening fail-closed for any other unknown provider.
- **L7 Model.** Env-configured with allowlist; default stays `claude-haiku-4-5-20251001`. Reviewer verified at platform.claude.com on 2026-10-05: Active, $1 / input MTok, $5 / output MTok. Rates stay in env (no prices hard-coded in src).
- **L8 SDK compatibility.** Repo pins anthropic 1.8.0. Python SDK v1.0+ removes temperature/top_p/top_k (TypeError if passed). Kwargs to `messages.create` are model/max_tokens/system/messages only.
- **L9 No UI change.** No FE files, no baseline changes, no STOP VISUAL. Visibility = startup_config non-secret flags + llm_calls.
- **L10 Hermetic and off elsewhere.** Anthropic never in tests or CI. `morning.yml` keeps `OPSPILOT_ANTHROPIC_ENABLED` literal `"false"`; morning_run preflight refusal stays; evals stay `"skipped"`.
- **L11 Docs.** This addendum (no D-034): operator-demo profile, allowlist ask+triage under L2, visitor exclusion, ledger + reservation policy, L4 rule, model/rate verification. New master record PART 20 (append-only; C9 after LIVE). Truth-align AGENTS.md, architecture, ROADMAP, README, `.env.example`, llm-providers runbook.
- **L12 Migration.** Prefer none. If one is needed: expand-only, new head, local Docker only in build; Neon is applied by the owner at STOP LIVE. **b6.1 ships with no migration.**

**Supersedes (CURRENT):** B2 addendum allowlist that excludes `ask`; env `OPSPILOT_ANTHROPIC_BUDGET_TOKENS`/`_USD` as runtime gate/seed (retired — CLI only; names remain only in the historical B2 table above).
