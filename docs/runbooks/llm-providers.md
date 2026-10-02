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

Resolution order (Gemini example): `GEMINI_MODEL_<TASK>` → `GEMINI_MODEL` → code default in `src/opspilot/llm/model_defaults.py`.

- **Ask:** `GEMINI_MODEL_ASK` (also `GROQ_MODEL_ASK`, `MISTRAL_MODEL_ASK`, …). Unset → same as provider default.
- **Verified free Gemini id in-repo:** only `gemini-3.5-flash-lite` (`GEMINI_DEFAULT_MODEL`). No stronger free-tier Gemini id is recorded in `model_defaults` / this runbook / `.env.example` — **do not invent** a “Pro/Flash” default; leave Ask on flash-lite unless the owner sets an explicit override after verifying free-tier availability.
| cloudflare | `@cf/meta/llama-3.3-70b-instruct-fp8-fast` | derived | 80 | 140000 | 10,000 neurons/day; 26,668 neurons/M input, 204,805 neurons/M output → ~177k tok/day at 5:1 in/out → `floor(0.8×177k)≈140000`; ~100 neurons/call → `floor(0.8×100)=80` REQ |
| openrouter | `nvidia/nemotron-3-super-120b-a12b:free` | mix | 40 | 160000 | Free tier 50 req/day → `floor(0.8×50)=40`; 20 RPM; **TOK_DAY OWNER POLICY** 160000. Model **must** keep `:free` suffix. |
| mistral | `ministral-3b-2512` | **OWNER POLICY** | 1000 | 1000000 | Headers: 750 RPM / 1,300,000 TPM only — **no daily quota**; policy caps (deviation from pure 80%) |
| ollama | local | unset | — | — | Optional local; leave budgets unset |
| anthropic | — | disabled | — | — | `OPSPILOT_ANTHROPIC_ENABLED=false` |

**Cloudflare neuron→token (document):** input 26,668 neurons per 1M tokens; output 204,805 neurons per 1M tokens. At a 5:1 in/out mix, 10k neurons/day ≈ ~177k tokens/day; 80% → 140k TOK_DAY. **Worst-case all-output** bound: 10,000 / 204,805 × 1e6 ≈ **48.8k tokens/day** if every token were output — stay under that when traffic is output-heavy.

**Policy-cap deviation:** Mistral (and OpenRouter/Gemini TOK_DAY policy values) are **OWNER POLICY** where daily measured RPD/TPD was missing or estimated — not pure `floor(0.8 × measured)`. Recorded in PART 7.

## Anthropic (D-023)

`OPSPILOT_ANTHROPIC_ENABLED=false` by default. Allowlisted tasks only (`demo_quality`, `leaderboard`, `judge_calibration`). Missing `OPSPILOT_ANTHROPIC_USD_PER_MTOK_IN` / `_OUT` while enabled → **never construct client**. Rates: **VERIFY AT DECISION TIME**.

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
