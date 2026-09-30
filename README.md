# OpsPilot AI

**Your AI chief of staff.** OpsPilot surfaces what needs attention, drafts the rest, and briefs you like a trusted advisor — calm UI, fictional demo data, local-first development.

[![CI](https://github.com/Settar-Mengli/opspilot-ai/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Settar-Mengli/opspilot-ai/actions/workflows/ci.yml)

**CURRENT on `main`:** B0–B2.1 merged (gateway + hardening). **Next:** B3 evals + red-team. See:

- [OPSPILOT-MASTER-RECORD.md](OPSPILOT-MASTER-RECORD.md) — history, baseline, locked plan
- [ROADMAP.md](ROADMAP.md) — batches **B0–B7** (+ B1.5 / B2.1)
- [docs/architecture.md](docs/architecture.md) — CURRENT vs TARGET
- [docs/design-decisions.md](docs/design-decisions.md) — portfolio ADR index
- [docs/adr/](docs/adr/) — ADRs D-001–D-029

Built with TypeScript, React, FastAPI, Postgres, and a **hand-rolled multi-provider LLM gateway** (free-tier Gemini → Groq → Mistral → Cloudflare → OpenRouter → Ollama → rules). Anthropic is prepaid-gated only (D-023; off by default).

> **Post-B2 note:** The [2026-09-25 baseline audit](docs/audits/2026-09-25-baseline-audit.md) scored AI engineering 2/5 **before** B2. That historical score is unchanged; CURRENT capability is the gateway described above.

---

## Screenshots (visual baselines)

Referenced from existing Playwright container baselines (not regenerated):

![Dashboard](frontend/e2e/visual.spec.ts-snapshots/dashboard-chromium-1280-linux.png)

![Briefing](frontend/e2e/visual.spec.ts-snapshots/briefing-chromium-1280-linux.png)

![Ask docked](frontend/e2e/visual.spec.ts-snapshots/ask-docked-messages-chromium-1280-linux.png)

---

## What it does today (CURRENT)

- Ingests fictional operational work items (JSON)
- Triages via free-tier gateway **or** deterministic rules when no key / `OPSPILOT_FORCE_RULES`
- `/api/v1` briefing / ask / evening / insights from **Postgres** (D-025)
- Mobile-first React dashboard + ≥1280 three-pane desktop shell
- Settings GET-only (`provider`, `model`, `api_key_set`)
- `LlmCall` traces + UTC-day budgets; `X-Request-ID` on requests

**Not yet:** public deploy, Neon hosted DB, eval harness metrics published, Gmail sync, agentic tools, Telegram morning run.

---

## AI stack (code paths)

| Layer | Path |
|-------|------|
| Policy / allow | `src/opspilot/llm/policy.py` (`llm_allowed`) |
| Production gateway | `src/opspilot/llm/routed.py` (`BudgetAwareGateway`) |
| Skeleton/test gateway | `src/opspilot/llm/gateway.py` (`LlmGateway` — test-only) |
| Providers | `src/opspilot/llm/providers/` (Gemini REST + OpenAI-compatible + D-023 Anthropic) |
| Services | `src/opspilot/services/` (ask / evening / insights) |
| Triage / briefing adapters | `src/opspilot/adapters/gateway_triage.py`, `briefing_adapter.py` |

### Request path

```mermaid
flowchart LR
  Client --> MW[RequestIdMiddleware]
  MW --> Routes["/api/v1 routes"]
  Routes --> Services[services / adapters]
  Services --> BAG[BudgetAwareGateway]
  BAG --> Providers[llm/providers]
  BAG --> LlmCall[(llm_calls)]
```

---

## Quick start (local)

Requires **Python 3.13**, **Node ≥24.15**, Docker (Postgres), and [uv](https://docs.astral.sh/uv/).

```powershell
docker compose up -d db
uv sync
if (-not (Test-Path .env)) { Copy-Item .env.example .env } else { Write-Host 'skip: .env exists' }
$env:DATABASE_URL='postgresql+psycopg://opspilot:opspilot@127.0.0.1:5432/opspilot'
uv run alembic upgrade head
uv run python -m opspilot.jobs.import_json data/raw/sample_input.json
uv run pytest -q
```

Backend:

```powershell
uv run uvicorn opspilot.api.app:app --app-dir src --reload --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd frontend
npm ci
npm run dev
```

**CLI export (files only, no DB):** `uv run python -m opspilot.cli run --output <dir> ...`
**Load files into DB:** `uv run python -m opspilot.jobs.import_json <path>` (X5).

Details: [docs/runbooks/local-dev.md](docs/runbooks/local-dev.md) · Zero-spend: [docs/runbooks/zero-spend.md](docs/runbooks/zero-spend.md)

---

## Roadmap (locked)

| Batch | Goal |
|-------|------|
| B0 | Docs & architecture lock |
| B1 | Hermetic foundation + SEC gate |
| B1.5a/b | UI safety net + desktop three-pane |
| B2 | LLM gateway + traces |
| B2.1 | Hardening + truth |
| B3 | Evals + injection red-team |
| B4 | Demo Google inbox/calendar |
| B5 | Agentic Ask + approve & send |
| B6 | Morning run + Telegram + preferences |
| B7 | Public free-tier deploy |

Full exits: [ROADMAP.md](ROADMAP.md).

---

## Design principles

1. Ground CURRENT vs TARGET honestly.
2. Zero further spend; free tiers + Ollama; Anthropic prepaid-gated only.
3. Hermetic tests — no live LLM in default suite/CI.
4. Calm UX — chief of staff, not alert spam.
