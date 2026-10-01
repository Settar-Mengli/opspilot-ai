# Local development runbook

## Prerequisites

- Python **3.13** (matches `requires-python` / CI)
- Node **24** (`.nvmrc` / `engines`)
- [uv](https://docs.astral.sh/uv/)
- Docker (Compose Postgres)
- Git

## Setup

```powershell
cd c:\Dev\opspilot-ai
docker compose up -d db
uv sync
uv run pre-commit install
if (-not (Test-Path .env)) { Copy-Item .env.example .env } else { Write-Host 'skip: .env exists' }
$env:DATABASE_URL='postgresql+psycopg://opspilot:opspilot@127.0.0.1:5432/opspilot'
uv run alembic upgrade head
```

**Do not put real API keys in `.env` for routine work.** Key check (True/False only — never print values):

```powershell
(Select-String -Path .env -Pattern '^\s*(ANTHROPIC_API_KEY|OPSPILOT_AI_API_KEY)\s*=\s*\S' -Quiet)
# Expect False
```

`OPSPILOT_FORCE_RULES` is **tests/CI only**, and until B2 it is **triage-factory-only** (the triage adapter factory honors it; evening/insights/briefing/conversation do not yet). Leave it commented in `.env.example`; never set it for normal demo or deploy.

## Seed / X5 importer

Load sample JSON into Postgres (idempotent by work-item `id` / `run_id`):

```powershell
uv run python -m opspilot.jobs.import_json data/raw/sample_input.json
```

## CLI vs API (D-025)

| Path | Writes files? | Writes Postgres? |
|------|---------------|------------------|
| API `POST /api/v1/runs` | No | Yes (only) |
| CLI `run --output <dir>` | Yes (required `--output`) | No |
| X5 `import_json` | No | Yes (from files) |

```powershell
# Files-only export (no DB):
uv run python -m opspilot.cli run --input data/raw/sample_input.json --output $env:TEMP\opspilot-cli-out --date 2026-09-26

# Then optionally load into DB:
uv run python -m opspilot.jobs.import_json $env:TEMP\opspilot-cli-out
```

## Stale venv lesson

If pytest shows mysterious import/CLI failures after package layout changes, **recreate `.venv`** (`Remove-Item -Recurse .venv; uv sync`) before debugging product code.

## Run backend

```powershell
$env:DATABASE_URL='postgresql+psycopg://opspilot:opspilot@127.0.0.1:5432/opspilot'
uv run uvicorn opspilot.api.app:app --app-dir src --reload --host 127.0.0.1 --port 8000
```

Use **127.0.0.1** (not `localhost`) for the API host so the operator session cookie matches the FE origin (A1).

## Run frontend

```powershell
cd frontend
npm ci
npm run dev -- --host 127.0.0.1 --port 5173
```

Open **http://127.0.0.1:5173** only. Mixing `localhost` and `127.0.0.1` breaks the cross-port operator cookie (FE→API credentials).

## Test / lint

```powershell
uv run ruff check .
uv run ruff format --check .
uv run mypy src/opspilot
uv run pytest -q
cd frontend; npm run lint; npm test -- --run; npm run build
```

## Canonical docs

- [OPSPILOT-MASTER-RECORD.md](../../OPSPILOT-MASTER-RECORD.md)
- [docs/architecture.md](../architecture.md)
- [zero-spend.md](zero-spend.md)
