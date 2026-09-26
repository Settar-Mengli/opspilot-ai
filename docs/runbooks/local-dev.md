# Local development runbook

## Prerequisites

- Python 3.11+ (local may be 3.13; CI may differ — note skew)
- Node 20+ / 24 OK
- Git

## Setup

```powershell
cd c:\Dev\opspilot-ai
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
if (-not (Test-Path .env)) { Copy-Item .env.example .env } else { Write-Host 'skip: .env exists' }
```

**Do not uncomment API keys until B1 hermetic guards land** (and even then, keep Anthropic commented for default work). Key check:

```powershell
(Select-String -Path .env -Pattern '^\s*(ANTHROPIC_API_KEY|OPSPILOT_AI_API_KEY)\s*=\s*\S' -Quiet)
# Expect False
```

## Stale venv lesson

If pytest shows mysterious import/CLI failures after package layout changes, **recreate `.venv`** before debugging product code. Operator note (2026-09): stale venv → 8 fail / 43 pass; fresh venv → 51 pass.

## Run backend

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn opspilot.api.app:app --reload --app-dir src
```

## Run frontend

```powershell
cd frontend
npm ci
npm run dev
```

## Test / lint

```powershell
uv run pytest -q
cd frontend; npm run lint; npm run build
```

## Canonical docs

- [OPSPILOT-MASTER-RECORD.md](../../OPSPILOT-MASTER-RECORD.md)
- [docs/architecture.md](../architecture.md)
- [zero-spend.md](zero-spend.md)
