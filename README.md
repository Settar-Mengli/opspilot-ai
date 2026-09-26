# OpsPilot AI

**Your AI chief of staff.** OpsPilot surfaces what needs attention, drafts the rest, and briefs you like a trusted advisor — calm UI, fictional demo data, local-first development.

**Rebuild in progress:** documentation and architecture are locked as **B0**. Runtime code at HEAD is still the pre-rebuild demo. See:

- [OPSPILOT-MASTER-RECORD.md](OPSPILOT-MASTER-RECORD.md) — history, baseline, locked plan
- [ROADMAP.md](ROADMAP.md) — batches **B0–B7**
- [docs/architecture.md](docs/architecture.md) — CURRENT vs TARGET
- [docs/adr/](docs/adr/) — ADRs D-001–D-023

Built with TypeScript, React, FastAPI, and (today) Anthropic Claude with a rule-based fallback. **TARGET** default path moves to free-tier Gemini → Groq → Ollama → rules; Anthropic becomes prepaid-gated only.

---

## What it does today (CURRENT)

- Ingests fictional operational work items (JSON)
- Triages via Claude **or** deterministic rules when no key
- Briefing / ask / evening / insights endpoints
- Mobile-first React dashboard
- Provider settings UI (conversation path); other adapters not fully migrated

**Not yet:** public deploy, Neon DB, multi-provider gateway, eval harness, Gmail sync, agentic tools, Telegram morning run.

---

## Quick start (local)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
if (-not (Test-Path .env)) { Copy-Item .env.example .env } else { Write-Host 'skip: .env exists' }

.venv\Scripts\python -m pytest -q

cd frontend
npm ci
npm run dev
```

Backend (separate terminal):

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn opspilot.api.main:app --reload --app-dir src
```

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
