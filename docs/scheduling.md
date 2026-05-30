# Local Scheduling (Design-Only)

## Status

Scheduling is not implemented in application code yet.

This document captures scope-safe guidance for future local scheduling and explicitly does not introduce cloud, auth, database, deployment, or external AI dependencies.

## Scope Guardrails

- Local-first only
- No cloud scheduler
- No auth or identity integration
- No database requirement for initial scheduling
- No external AI/LLM providers

## Current Operational Model

- Pipeline can be run manually via CLI or API.
- Latest outputs are written to `data/output/`.
- Immutable history artifacts are written to `data/history/runs/...`.

## Recommended First Scheduling Path

For Windows environments, prefer **Windows Task Scheduler** invoking the existing CLI command.

Example command pattern:

```powershell
python -m opspilot.cli run --input data/raw/sample_input.json --output data/output --date YYYY-MM-DD
```

Use a wrapper PowerShell script only if needed for:

- activating the project virtual environment
- setting project working directory
- writing a local log file

## Why Task Scheduler First

- Uses existing deterministic pipeline and contracts unchanged
- Requires no always-on application process
- Fits local-first constraints and portfolio demo expectations
- Avoids introducing background-worker complexity early

## Not Included Yet

- In-app scheduler daemon
- APScheduler/background loop in FastAPI
- Hosted cron jobs
- Notification delivery integrations

## Future Documentation Follow-Up

When scheduling is implemented, update:

- `README.md` (operator runbook section)
- `docs/architecture.md` (scheduler boundary)
- `docs/demo.md` (demo script)
- `CHANGELOG.md` and `PROGRESS.md` (delivery trace)
