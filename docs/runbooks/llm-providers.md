# LLM providers runbook (B2)

## Default path

Free-tier order via `INFERENCE_PROVIDER_ORDER` (default `gemini,groq,mistral,cloudflare,openrouter`). Anthropic is **never** in that list. Final fallback: rules / soft strings / template briefing.

## Keys (never print values)

| Provider | Env |
|----------|-----|
| Gemini | `GEMINI_API_KEY`, `GEMINI_MODEL`, optional `GEMINI_MODEL_<TASK>` |
| Groq | `GROQ_API_KEY`, `GROQ_MODEL`, optional `GROQ_MODEL_<TASK>` |
| Mistral | `MISTRAL_API_KEY`, `MISTRAL_MODEL`, … |
| Cloudflare | `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_MODEL` |
| OpenRouter | `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` |
| Ollama | `OLLAMA_BASE_URL`, `OLLAMA_MODEL` |
| Anthropic (gated) | `ANTHROPIC_API_KEY` + D-023 env (see below) |

Retired: `OPSPILOT_AI_API_KEY` / `OPSPILOT_AI_PROVIDER` / `OPSPILOT_AI_MODEL`.

## Budgets (UTC day)

Per provider: `OPSPILOT_BUDGET_<PROVIDER>_REQ_DAY` and `_TOK_DAY`.

- Unset/empty → **deny** remote for that provider (no invented defaults).
- Atomic debit: `INSERT … ON CONFLICT DO NOTHING` then `UPDATE … WHERE req_count < :cap RETURNING …`.
- Token cap reconciled **post-call** — may overshoot by ≤1 call (use 80% margin).
- Budget day is **UTC**; Gemini dashboard RPD may be Pacific — document skew when setting caps.

## Anthropic (D-023)

`OPSPILOT_ANTHROPIC_ENABLED=false` by default. Allowlisted tasks only (`demo_quality`, `leaderboard`, `judge_calibration`). Missing `OPSPILOT_ANTHROPIC_USD_PER_MTOK_IN` / `_OUT` while enabled → **never construct client**. Rates: **VERIFY AT DECISION TIME**.

## Discovery (STOP A)

```powershell
uv run python -m opspilot.jobs.llm_discover
```

Never prints key values. Supplement with dashboard-only numbers (AI Studio, Cloudflare neurons, OpenRouter free). Approve `floor(0.8 × measured)` before writing caps into `.env`.

## Live smoke (Invoke-RestMethod — not curl)

```powershell
cd C:\Dev\opspilot-ai
uv run alembic upgrade head
# Set OPSPILOT_ANTHROPIC_ENABLED=false; set budget env for free providers; Postgres up
uv run uvicorn opspilot.api.app:app --host 127.0.0.1 --port 8000
# Separate shell:
$base = "http://127.0.0.1:8000"
Invoke-RestMethod -Method Post -Uri "$base/api/v1/ask" -ContentType "application/json" -Body '{"question":"What needs attention?","assistant_name":"OpsPilot"}'
```

Forced failover: invalidate `GEMINI_API_KEY` in the uvicorn process only; expect gemini attempt fail + next provider success. Policy deny: `OPSPILOT_LLM_DISABLE=1`.

## X4 / data use

Unpaid Gemini (and some free tiers) **may train on prompts**. Fictional data only; minimize PII in prompts. Terms VERIFY AT DECISION TIME.

## Related

- [zero-spend.md](zero-spend.md)
- ADRs D-012 / D-019 / D-023
