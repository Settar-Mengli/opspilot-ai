# D-025: Run history SoT = Postgres (supersedes D-006 file primacy)

- **Date:** 2026-09-26
- **Status:** Accepted
- **Blocks:** B1+
- **Supersedes:** D-006 (file-based history as primary API read path)

## Context

D-006 made `data/history` the read path for runs. B1 introduces Postgres persistence and `/api/v1` reads from the database.

## Decision

After B1 commit 6+, **Postgres `runs` / `run_artifacts` / `triage_decisions` / `work_items` are authoritative** for API reads. The file pipeline still writes `data/output` and `data/history` as artifacts/export; X5 imports those into Postgres idempotently by `run_id` / work-item `id`.

## Consequences

Frontend and `/api/v1` do not depend on filesystem history for list/get. Smoke and CI use Postgres.
