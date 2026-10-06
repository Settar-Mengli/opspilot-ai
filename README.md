# OpsPilot AI

**Your AI chief of staff.** OpsPilot triages operational work, drafts replies you approve before send, and briefs you in a calm local UI. Demo data is fictional. There is no public deployment — this repo is the portfolio artifact.

[![CI](https://github.com/Settar-Mengli/opspilot-ai/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Settar-Mengli/opspilot-ai/actions/workflows/ci.yml)

Stack: TypeScript, React, FastAPI, Postgres, and a hand-rolled multi-provider LLM gateway. Default free-tier order is Gemini → Groq → Mistral → Cloudflare → OpenRouter. If every remote provider fails or is denied, triage falls back to deterministic rules. Ollama is supported when listed in `INFERENCE_PROVIDER_ORDER` (not in the default order). Anthropic is prepaid-gated, operator-only, and off by default.

---

## Screenshots

Playwright container baselines (CI visual suite). Captions describe the state shown.

### Desktop (1280)

Dashboard — home, SAMPLE briefing line, action hub, docked Ask rail:

![Dashboard desktop](frontend/e2e/visual.spec.ts-snapshots/dashboard-chromium-1280-linux.png)

Ask docked — three-pane shell with a short triage answer in the Ask rail:

![Ask docked with messages](frontend/e2e/visual.spec.ts-snapshots/ask-docked-messages-chromium-1280-linux.png)

Briefing — today’s briefing with Critical / High / Can wait counts:

![Briefing desktop](frontend/e2e/visual.spec.ts-snapshots/briefing-chromium-1280-linux.png)

Items split — full picture list with a selected item detail pane:

![Items split desktop](frontend/e2e/visual.spec.ts-snapshots/items-split-chromium-1280-linux.png)

### Mobile (375)

Dashboard — mobile home and bottom Ask bar:

![Dashboard mobile](frontend/e2e/visual.spec.ts-snapshots/dashboard-chromium-375-linux.png)

Ask — mobile Ask panel with the same triage exchange:

![Ask with messages mobile](frontend/e2e/visual.spec.ts-snapshots/ask-with-messages-chromium-375-linux.png)

Items — urgency-grouped queue (High / Medium / Low):

![Items mobile](frontend/e2e/visual.spec.ts-snapshots/items-chromium-375-linux.png)

---

## What it does

- Ingests fictional work items from JSON, and syncs operator Gmail + Calendar when Google OAuth is connected (Testing app; `DEMO_MODE` blocks OAuth/sync/send for visitors).
- Triages items through the gateway with structured JSON (urgency, category, sentiment, confidence, evidence refs), or via rules when remote LLM is disabled.
- Serves briefing, Ask, evening wrap-up, and insights from Postgres over `/api/v1`.
- Runs a bounded Ask agent (search / get message / calendar / draft reply) over SSE. There is no model-callable send tool.
- Human-in-the-loop mail: edit draft, approve, then send to an allowlisted recipient (operator only).
- Morning job on GitHub Actions (`schedule: 0 12 * * *` UTC + `workflow_dispatch`) with counts-only Telegram notify. First scheduled end-to-end success: run [37507785445](https://github.com/Settar-Mengli/opspilot-ai/actions/runs/37507785445) (2026-10-06).
- Optional GitHub MCP read-only Ask tools (flag off by default; operator-local; not used in CI).
- Mobile-first UI; at ≥1280 a three-pane desktop shell with a docked Ask rail.

## What it does not do

- No public hosted demo (B7 is backlog).
- Disconnecting Google removes credentials and sync cursors; it does **not** delete already-synced mail/calendar rows.
- Free hosted LLM providers may use prompts under their own terms. Local Ollama or `OPSPILOT_FORCE_RULES` avoid remote inference. Details: [docs/trust-and-data.md](docs/trust-and-data.md).

---

## AI engineering (CURRENT)

| Piece | Behavior | Code |
|-------|----------|------|
| Gateway | Ordered failover, circuit breaker, UTC-day request/token budgets, `LlmCall` traces | `src/opspilot/llm/routed.py`, `budgets.py` |
| Structured outputs | Schema-validated JSON + one repair attempt | `routed.py` `complete_json`, `src/opspilot/llm/schemas/` |
| Policy | `OPSPILOT_FORCE_RULES` / `OPSPILOT_LLM_DISABLE` block remote LLM | `src/opspilot/llm/policy.py` |
| Anthropic | Off by default; operator Ask/Sync only; token + USD prepaid ledger | D-023, `anthropic_budget` repo |
| Injection defenses | Neutralize + untrusted delimiters; triage body cap 500 chars; grounding on evidence refs | `gateway_triage.py`, D-029 |
| Ask agent | JSON tool turns; step/provider caps; SSE events | `src/opspilot/agent/loop.py`, D-031/D-032 |
| HITL send | Approve path; recipient allowlist; DEMO_MODE deny | `mail_hitl.py`, D-033 |
| Evals | Hermetic rules macro-F1 floor **0.30** (n=40) in CI; live leaderboard in-repo | `rules_baseline.py`, `docs/evals/leaderboard.md` |
| Red-team | Hermetic corpus n=20; live ASR reported, not CI-gated | `evals/datasets/redteam/v1/` |

---

## Evidence

Measured on `main` tip CI run [37531681964](https://github.com/Settar-Mengli/opspilot-ai/actions/runs/37531681964) (`82515df`, 2026-10-06) unless noted:

- Backend: **659** tests passed; coverage **82.85%** (gate **72%**).
- Frontend unit: **49** passed.
- Visual regression: **90** committed Playwright baselines across viewports 375, 768, and 1280.
- Hermetic CI floor: rules macro-F1 ≥ **0.30** on triage n=40.
- Live triage (accepted-only F1; see leaderboard for artifacts and dates): Gemini **0.606** (n=40); Groq **0.613** (n=40); Mistral **0.537** (n=40); Cloudflare combined **0.706** (n=40); OpenRouter **0.619** (**n=15**, partial — red-team not run). Anthropic skipped.

Full live table: [docs/evals/leaderboard.md](docs/evals/leaderboard.md).

---

## Trust and data

Mail and triage text sent to an LLM is capped and wrapped as untrusted content. Attachments are not ingested. Sending mail always requires an explicit approve step. Anthropic and GitHub MCP stay off unless the operator enables them locally.

What is not solved: deletion of synced rows on disconnect; full provider retention terms for every free-tier vendor.

→ [docs/trust-and-data.md](docs/trust-and-data.md)

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

Backend: `uv run uvicorn opspilot.api.app:app --app-dir src --reload --host 127.0.0.1 --port 8000`

Frontend: `cd frontend && npm ci && npm run dev`

More: [docs/runbooks/local-dev.md](docs/runbooks/local-dev.md) · [docs/runbooks/zero-spend.md](docs/runbooks/zero-spend.md)

---

## Docs

- [docs/architecture.md](docs/architecture.md) — CURRENT vs TARGET
- [docs/trust-and-data.md](docs/trust-and-data.md) — fields, caps, provider tiers
- [docs/evals/leaderboard.md](docs/evals/leaderboard.md) — live eval numbers
- [docs/design-decisions.md](docs/design-decisions.md) — ADR index (D-001–D-034)
- [docs/adr/](docs/adr/) — decision records
- [ROADMAP.md](ROADMAP.md) — batches B0–B6; B7 backlog
- [OPSPILOT-MASTER-RECORD.md](OPSPILOT-MASTER-RECORD.md) — history and locked plan
