# D-025: Run history SoT = Postgres (supersedes D-006 file primacy)

- **Date:** 2026-09-26
- **Status:** Accepted (revised B1 fix pass)
- **Blocks:** B1+
- **Supersedes:** D-006
- **Owner ruling:** O2 (B1 fix pass)

## Context

D-006 made `data/history` the API read path. B1 introduced Postgres. API runs previously still wrote `data/output` / `data/history`, polluting hermetic tests.

## Decision

**Postgres (`runs`, `run_artifacts`, `triage_decisions`, `work_items`) is the source of truth** for all `/api/v1` reads and for runs triggered through the API.

**Files are written only on explicit CLI export.** The CLI `run` command writes artifacts to the required `--output` directory **only** and does **not** persist to Postgres. Getting CLI file output into the DB is a separate step via the **X5 importer** (`python -m opspilot.jobs.import_json` / history import).

API request paths must not create or depend on `data/output` or `data/history`; API runs persist to Postgres only.

X5 imports JSON sample / history fixtures (including prior CLI exports) into Postgres idempotently by work-item `id` / `run_id`.

## Consequences

Frontend and `/api/v1` never require filesystem history. Hermetic tests must not create repo `data/output` or `data/history`. Smoke proves API POST leaves those trees unchanged. local-dev documents: CLI `--output` = files only (no DB); X5 importer = DB load from files.
