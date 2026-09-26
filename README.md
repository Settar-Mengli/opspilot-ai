# OpsPilot AI

**Your AI chief of staff.** OpsPilot surfaces what needs attention, drafts the rest, and briefs you like a trusted advisor — calm UI, fictional demo data, local-first development.

**Rebuild in progress:** B0 docs lock is on `main`; B1 hermetic foundation is on branch `b1/hermetic-foundation`. See:

- [OPSPILOT-MASTER-RECORD.md](OPSPILOT-MASTER-RECORD.md) — history, baseline, locked plan
- [ROADMAP.md](ROADMAP.md) — batches **B0–B7**
- [docs/architecture.md](docs/architecture.md) — CURRENT vs TARGET
- [docs/adr/](docs/adr/) — ADRs D-001–D-025

Built with TypeScript, React, FastAPI, Postgres, and (today) Anthropic Claude with a rule-based fallback. **TARGET** default path moves to free-tier Gemini → Groq → Ollama → rules; Anthropic becomes prepaid-gated only.

---

## What it does today (CURRENT)

- Ingests fictional operational work items (JSON)
- Triages via Claude **or** deterministic rules when no key / `OPSPILOT_FORCE_RULES`
- `/api/v1` briefing / ask / evening / insights from **Postgres** (D-025)
- Mobile-first React dashboard on `/api/v1`
- Settings GET-only (`provider`, `model`, `api_key_set`)

**Not yet:** public deploy, Neon hosted DB, multi-provider gateway, eval harness, Gmail sync, agentic tools, Telegram morning run.

---

## Quick start (local)

Requires **Python 3.13**, **Node 24**, Docker (Postgres), and [uv](https://docs.astral.sh/uv/).

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
| B2 | LLM gateway + traces |
| B3 | Evals + injection red-team |
| B4 | Demo Google inbox/calendar |
| B5 | Agentic Ask + approve & send |
| B6 | Morning run + Telegram + preferences |
| B7 | Public free-tier deploy |

Full exits: [ROADMAP.md](ROADMAP.md).

---

## Design principles

1. The AI provider is a commodity; the product is the chief-of-staff workflow.
2. Adapter / gateway seams — no provider SDK sprawl in features.
3. Zero further spend; hermetic CI.
4. Calm by default — advisor voice, not alert spam.

---

## License

MIT — see [LICENSE](LICENSE).
