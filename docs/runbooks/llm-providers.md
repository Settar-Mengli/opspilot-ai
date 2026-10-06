# LLM providers runbook (B2)

## Default path

Free-tier order via `INFERENCE_PROVIDER_ORDER` (default `gemini,groq,mistral,cloudflare,openrouter`). Anthropic is **never** in that list. Final fallback: rules / soft strings / template briefing.

## Keys (never print values)

| Provider | Env |
|----------|-----|
| Gemini | `GEMINI_API_KEY`, `GEMINI_MODEL`, optional `GEMINI_MODEL_<TASK>` (e.g. `GEMINI_MODEL_ASK`) |
| Groq | `GROQ_API_KEY`, `GROQ_MODEL`, optional `GROQ_MODEL_<TASK>` |
| Mistral | `MISTRAL_API_KEY`, `MISTRAL_MODEL`, … |
| Cloudflare | `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_MODEL` |
| OpenRouter | `OPENROUTER_API_KEY`, `OPENROUTER_MODEL=nvidia/nemotron-3-super-120b-a12b:free` (**must keep `:free`**) |
| Ollama | `OLLAMA_BASE_URL`, `OLLAMA_MODEL` |
| Anthropic (gated) | `ANTHROPIC_API_KEY` + D-023 env (see below) |

Retired: `OPSPILOT_AI_API_KEY` / `OPSPILOT_AI_PROVIDER` / `OPSPILOT_AI_MODEL`.

## Budgets (UTC day)

Per provider: `OPSPILOT_BUDGET_<PROVIDER>_REQ_DAY` and `_TOK_DAY`.

- Unset/empty → **deny** remote for that provider (no invented defaults). Applies to **ask, evening, insights, triage, and briefing** — all use `BudgetAwareGateway` + DB session. No session → deny → soft/rules/template.
- Atomic debit: `INSERT … ON CONFLICT DO NOTHING` then `UPDATE … WHERE req_count < :cap RETURNING …`.
- Token cap reconciled **post-call** — may overshoot by ≤1 call (use 80% margin).
- Budget day is **UTC**; Gemini AI Studio free RPD resets at **Pacific midnight** — UTC day can span two Gemini days; keep 80% margin.
- `complete_json` repair attempts debit a **second** request against the same provider.
- Schema/format HTTP **400** on native schema mode: one same-provider **`json_object` retry** (also budget-debited; own `LlmCall` row), then failover.
- Structured contracts: non-empty insights queue requires ≥1 insight; empty queue soft-paths without LLM. See D-013 addendum.

### Owner-approved recommended defaults (2026-09-29)

Copied into `.env.example`. Apply the same lines to local `.env` (budget vars only).

| Provider | Model | Cap type | REQ_DAY | TOK_DAY | Source / method |
|----------|-------|----------|---------|---------|-----------------|
| groq | `openai/gpt-oss-20b` | `floor(0.8 × measured)` | 800 | 160000 | Headers: 1,000 RPD, 8,000 TPM; published 200,000 TPD → `floor(0.8×1000)=800`, `floor(0.8×200000)=160000` |
| gemini | `gemini-3.5-flash-lite` | mix | 400 | 800000 | AI Studio free 500 RPD → `floor(0.8×500)=400`; **TOK_DAY OWNER POLICY** = 400 × ~2,000 tokens |

### Per-task model overrides (CURRENT)

Resolution order (Gemini):

- **Ask:** `GEMINI_MODEL_ASK` → code default `GEMINI_ASK_DEFAULT_MODEL` = **`gemini-3.8-flash`** (does **not** fall through to `GEMINI_MODEL`).
- **Other tasks:** `GEMINI_MODEL_<TASK>` → `GEMINI_MODEL` → `GEMINI_DEFAULT_MODEL` = `gemini-3.5-flash-lite`.

**Ask model verification (2026-10-02):** `GET https://generativelanguage.googleapis.com/v1beta/models` (`models.list`) with the project key. Chose strongest **non-Pro Flash**, **non-Lite**, `generateContent`-capable, **non-preview** id from that list: `gemini-3.8-flash` (vs `gemini-3.7-flash` / `3.6` / `3.5` / `2.5-flash`). Pro / Lite / preview / image / TTS / live aliases excluded.
| cloudflare | `@cf/meta/llama-3.3-70b-instruct-fp8-fast` | derived | 80 | 140000 | 10,000 neurons/day; 26,668 neurons/M input, 204,805 neurons/M output → ~177k tok/day at 5:1 in/out → `floor(0.8×177k)≈140000`; ~100 neurons/call → `floor(0.8×100)=80` REQ |
| openrouter | `nvidia/nemotron-3-super-120b-a12b:free` | mix | 40 | 160000 | Free tier 50 req/day → `floor(0.8×50)=40`; 20 RPM; **TOK_DAY OWNER POLICY** 160000. Model **must** keep `:free` suffix. |
| mistral | `ministral-3b-2512` | **OWNER POLICY** | 1000 | 1000000 | Headers: 750 RPM / 1,300,000 TPM only — **no daily quota**; policy caps (deviation from pure 80%) |
| ollama | local | unset | — | — | Optional local; leave budgets unset |
| anthropic | — | disabled | — | — | `OPSPILOT_ANTHROPIC_ENABLED=false` |

**Cloudflare neuron→token (document):** input 26,668 neurons per 1M tokens; output 204,805 neurons per 1M tokens. At a 5:1 in/out mix, 10k neurons/day ≈ ~177k tokens/day; 80% → 140k TOK_DAY. **Worst-case all-output** bound: 10,000 / 204,805 × 1e6 ≈ **48.8k tokens/day** if every token were output — stay under that when traffic is output-heavy.

**Policy-cap deviation:** Mistral (and OpenRouter/Gemini TOK_DAY policy values) are **OWNER POLICY** where daily measured RPD/TPD was missing or estimated — not pure `floor(0.8 × measured)`. Recorded in PART 7.

## Anthropic (D-023 / b6.1 CURRENT)

`OPSPILOT_ANTHROPIC_ENABLED=false` by default. **CURRENT:** Operator-only Ask SSE + Sync drain triage when authorized (`demo_operator` cookie + ENABLED + DEMO off + prepaid ledger). Off by default; never visitors. Visitors / morning job / evals never call Anthropic. Missing positive `OPSPILOT_ANTHROPIC_USD_PER_MTOK_IN` / `_OUT` while enabled → never construct client. Rates verified platform.claude.com 2026-10-05: $1 / $5 MTok. Default model `claude-haiku-4-5-20251001`. SDK timeout default 25s (`OPSPILOT_ANTHROPIC_TIMEOUT_S`); Ask step wall remains 30s.

**LIVE PASS (owner-run 2026-10-05, Neon host `ep-withered-dew-b528cx5k-pooler`):** L0–L10 completed; total measured spend 5269 tokens / USD 0.007589; final restore `anthropic_rows_total=5`, ledger remaining 1 / 0.000001, `open_reservations=0` at every check. Full counts in PART 20.

**Ledger CLI — sole writer of `anthropic_prepaid_budget` (no env seed; retired `OPSPILOT_ANTHROPIC_BUDGET_*` names are gone):**

```powershell
uv run python -m opspilot.jobs.db_host
uv run python -m opspilot.jobs.anthropic_budget show
uv run python -m opspilot.jobs.anthropic_budget set --tokens 100000 --usd 0.30
# non-local hosts require: --confirm-host <label>
```

`show` prints `remaining_*`, `anthropic_rows_total`, `open_reservations`, `by_status` (excludes open reservations), `by_task`, `max_id`. Startup refuse if ENABLED ∧ DEMO_MODE. Morning `_preflight()` raises `PreflightError("anthropic_enabled")` when enabled.

### STOP LIVE (operator demo; process env only — never commit `.env`)

Owner sets **process env only** on the API host (names in chat; never commit `.env`):

- `ANTHROPIC_API_KEY`
- `OPSPILOT_ANTHROPIC_ENABLED=true`
- `OPSPILOT_ANTHROPIC_USD_PER_MTOK_IN=1`
- `OPSPILOT_ANTHROPIC_USD_PER_MTOK_OUT=5`
- `ANTHROPIC_MODEL=claude-haiku-4-5-20251001`
- `OPSPILOT_DEMO_MODE=0`
- Optional: `OPSPILOT_ANTHROPIC_TIMEOUT_S=25`

**Database:** owner chooses (local Docker **or** Neon). Non-local `set` needs `--confirm-host`. LIVE needs a **Google-connected operator session** in the browser on `http://127.0.0.1:5173` (API `http://127.0.0.1:8000`) so Sync triage can run. **No raw SQL** — use `anthropic_budget show` only. No secrets, mail content, or addresses in expected output. After every completed step, `show` must report `open_reservations=0`.

**Morning preflight (CURRENT):** `_preflight() -> None` in `src/opspilot/jobs/morning_run.py`; raises `PreflightError("anthropic_enabled")` when `anthropic_enabled()` is true.

```powershell
# L0 — host label
uv run python -m opspilot.jobs.db_host
# expect: database host=<label>
# record LABEL

# L1 — baseline (counts only)
uv run python -m opspilot.jobs.anthropic_budget show
# expect: database host=<label>
# expect line: anthropic_rows_total=<N0>
# expect line: open_reservations=0
# expect lines: by_status=... ; by_task=... ; max_id=...
# record N0 and MAX0

# L2 — set LIVE ledger
uv run python -m opspilot.jobs.anthropic_budget set --tokens 100000 --usd 0.30
# if non-local: append --confirm-host <LABEL>
# expect: exit 0; remaining_tokens=100000; remaining_usd=0.30

uv run python -m opspilot.jobs.anthropic_budget show
# expect: remaining_tokens=100000; remaining_usd=0.30; anthropic_rows_total=N0; open_reservations=0

# L3 — start API with STOP SECRETS process env. Frontend: npm run dev on 127.0.0.1:5173
# expect startup_config contains: ANTHROPIC_ENABLED=1 ANTHROPIC_LEDGER=1

# L4 — operator Ask (browser, operator cookie, one short fictional question via Ask SSE)
uv run python -m opspilot.jobs.anthropic_budget show
# expect: anthropic_rows_total=N1 where N1 > N0
# expect: open_reservations=0
# expect: by_status includes success:<s> with s >= 1
# expect: by_task includes ask:<a> with a >= 1
# expect: max_id > MAX0
# expect: remaining_tokens < 100000 OR remaining_usd < 0.30
# record N1, MAX1, remaining after Ask (TOK1, USD1)

# L5 — no-cookie Ask (exact request; no Cookie header)
uv run python -m opspilot.jobs.anthropic_budget show
# record N_before_nocookie (= current anthropic_rows_total)

Invoke-RestMethod -Method POST -Uri 'http://127.0.0.1:8000/api/v1/ask/stream' `
  -ContentType 'application/json' `
  -Headers @{ Origin = 'http://127.0.0.1:5173' } `
  -Body '{"question":"ping","assistant_name":"OpsPilot","history":[]}'
# expect: stream completes without API process crash

uv run python -m opspilot.jobs.anthropic_budget show
# expect: anthropic_rows_total == N_before_nocookie
# expect: open_reservations=0
# assert: anthropic row delta = 0

# L6 — one-item Sync triage (browser Connections Sync; exactly one untriaged gmail item)
uv run python -m opspilot.jobs.anthropic_budget show
# expect: anthropic_rows_total=N2 where N2 > N1
# expect: open_reservations=0
# expect: by_task includes triage:<t> with t >= 1
# expect: remaining below post-L4 (TOK1/USD1)

# L7 — exhaustion drill
uv run python -m opspilot.jobs.anthropic_budget set --tokens 1 --usd 0.000001
# if non-local: --confirm-host <LABEL>
# expect: remaining_tokens=1; remaining_usd=0.000001

uv run python -m opspilot.jobs.anthropic_budget show
# expect: open_reservations=0
# record success count S0 from by_status

# Operator Ask again (browser, operator cookie)
uv run python -m opspilot.jobs.anthropic_budget show
# expect: by_status success count == S0  (zero new anthropic success rows)
# expect: remaining_tokens=1; remaining_usd=0.000001  (ledger unchanged)
# expect: open_reservations=0
# note: anthropic_rows_total MAY rise — pre-reserve budget_denied rows are still recorded
#       when ENABLED is on; only success count and ledger remaining must stay flat
# expect: Ask still answered (SSE final/token from free path or soft string — not an empty crash)

# L8 — flag-off restart
# Restart API with OPSPILOT_ANTHROPIC_ENABLED unset/false
uv run python -m opspilot.jobs.anthropic_budget show
# record N_flag0 = anthropic_rows_total
# expect: open_reservations=0

# Operator Ask (browser)
uv run python -m opspilot.jobs.anthropic_budget show
# expect: anthropic_rows_total == N_flag0
# expect: open_reservations=0
# assert: delta = 0

# L9 — morning preflight refusal (real function)
$env:OPSPILOT_ANTHROPIC_ENABLED = '1'
uv run python -c "from opspilot.jobs.morning_run import _preflight; _preflight()"
# expect: raises PreflightError with anthropic_enabled; non-zero exit
Remove-Item Env:OPSPILOT_ANTHROPIC_ENABLED -ErrorAction SilentlyContinue

# L10 — restore
# Ensure API process has OPSPILOT_ANTHROPIC_ENABLED unset; restart if needed
uv run python -m opspilot.jobs.anthropic_budget show
# expect: open_reservations=0
# LIVE PASS 2026-10-05 restore state (Neon): remaining_tokens=1 remaining_usd=0.000001
#   anthropic_rows_total=5; open_reservations=0 (see PART 20)
```

## Discovery (STOP A)

```powershell
uv run python -m opspilot.jobs.llm_discover
```

Never prints key values. Supplement with dashboard-only numbers (AI Studio, Cloudflare neurons, OpenRouter free). Caps locked after owner **quotas approved** (PART 7 C11).

## Live smoke (Invoke-RestMethod — not curl)

```powershell
cd C:\Dev\opspilot-ai
uv run alembic upgrade head
# OPSPILOT_ANTHROPIC_ENABLED=false; approved OPSPILOT_BUDGET_* in .env; Postgres up
uv run uvicorn opspilot.api.app:app --host 127.0.0.1 --port 8000
# Separate shell:
$base = "http://127.0.0.1:8000"
Invoke-RestMethod -Method Post -Uri "$base/api/v1/ask" -ContentType "application/json" -Body '{"question":"What needs attention?","assistant_name":"OpsPilot"}'
```

Forced failover: set invalid `GEMINI_API_KEY` in the **uvicorn process environment only** (never edit `.env`); expect gemini attempt fail + next provider success. Policy deny: `OPSPILOT_LLM_DISABLE=1`. Budget deny: set one provider `_REQ_DAY=0` in the process only.

Status counts one-liner (redacted; no keys):

```powershell
uv run python -c "from opspilot.persistence.db import create_engine, create_session_factory, get_database_url; from sqlalchemy import text; s=create_session_factory(create_engine(get_database_url()))(); rows=s.execute(text('SELECT provider, status, COUNT(*) FROM llm_calls GROUP BY 1,2 ORDER BY 1,2')).all(); print('\n'.join(f'{p} {st} {c}' for p,st,c in rows))"
```

## X4 / data use

Unpaid Gemini (and some free tiers) **may train on prompts**. Fictional data only; minimize PII in prompts. Terms VERIFY AT DECISION TIME.

## Related

- [zero-spend.md](zero-spend.md)
- ADRs D-012 / D-019 / D-023
