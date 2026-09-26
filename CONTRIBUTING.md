# Contributing

Thanks for contributing to OpsPilot AI.

## Principles

- Keep changes scoped and purposeful.
- Prefer deterministic, testable behavior.
- Distinguish CURRENT (verified) from TARGET (planned).
- Update docs when behavior or process changes.
- Follow [AGENTS.md](AGENTS.md) (zero-spend, hermetic tests, cut-list discipline, plan gate).

## Workflow (Ask → Plan → Build)

1. **Ask** — read-only analysis; no file writes.
2. **Plan** — one large batch plan; must satisfy AGENTS **Plan requirements** (10 items); Build only after owner confirmation.
3. **Build** — implement only the approved batch; small commits inside the batch; each leaves tests green.
4. After Build — **Ask audit** → one **fix pass** (commit, push, open PR). Agent **never merges**; operator merges after CI green.
5. **Live smoke** before PR.

Explain before edit. Implementation report after each coding step.

## Branch naming

**Required for roadmap batches:** one branch per batch from updated `main`:

- `b0/docs-architecture-lock`
- `b1/...`, `b2/...`, …

Also acceptable for tiny out-of-band fixes (still no merge by agent):

- `feat/<short-topic>` · `fix/<short-topic>` · `docs/<short-topic>` · `chore/<short-topic>` · `test/<short-topic>`

## Commit messages

Conventional Commits: `feat:` · `fix:` · `docs:` · `test:` · `chore:`

## Pull requests

- One intent per PR (usually one batch).
- Include testing notes, live-smoke commands, and a short implementation report.
- Do not merge CUT-list or out-of-batch scope without an explicit decision.
- Agent opens PR; operator merges.

## Local validation (typical)

```powershell
docker compose up -d db
uv sync --extra dev
$env:DATABASE_URL='postgresql+psycopg://opspilot:opspilot@127.0.0.1:5432/opspilot'
uv run alembic upgrade head
uv run pytest -q --randomly-seed=1
uv run ruff check .
uv run mypy src/opspilot
cd frontend; npm ci; npm run lint; npm test -- --run; npm run build
```

API entrypoint: `uv run uvicorn opspilot.api.app:app --app-dir src --reload`

Guarded env template (never overwrite an existing `.env`):

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env } else { Write-Host 'skip: .env exists' }
```

Key check (True/False only — **never print** `.env` contents):

```powershell
(Select-String -Path .env -Pattern '^\s*(ANTHROPIC_API_KEY|OPSPILOT_AI_API_KEY)\s*=\s*\S' -Quiet)
```

Expect **False** during zero-spend hermetic work unless running an explicit budgeted operator script.

## Documentation sources of truth

| Topic | File |
|-------|------|
| Locked plan | `OPSPILOT-MASTER-RECORD.md` |
| Batches B0–B7 | `ROADMAP.md` |
| CURRENT vs TARGET architecture | `docs/architecture.md` |
| Decisions | `docs/adr/` |
| Agent rules + plan gate | `AGENTS.md` |
| Runbooks | `docs/runbooks/` |
