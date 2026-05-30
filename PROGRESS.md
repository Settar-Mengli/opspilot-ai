# Progress

## Commit Log

- Date: 2026-05-29
- Status: Commit 1 initialized
- Summary: Established trust/governance files and CI skeleton before source code.
- Completed:
  - Added `README.md`
  - Added `AGENTS.md`
  - Added `PROGRESS.md`
  - Added `LICENSE`
  - Added `CHANGELOG.md`
  - Added `CONTRIBUTING.md`
  - Added `.gitignore`
  - Added `.github/workflows/ci.yml`

- Date: 2026-05-29
- Status: Commit 2 completed
- Summary: Added concise architecture and product-definition docs.
- Completed:
  - Added `docs/milestones.md`
  - Added `docs/architecture.md`
  - Added `docs/decisions.md`
  - Added `docs/glossary.md`
  - Added `docs/demo.md`
  - Added `docs/copilot-workflow.md`
  - Added `docs/ai-memory/README.md`

- Date: 2026-05-29
- Status: Commit 3 implemented
- Summary: Delivered first runnable local vertical slice with deterministic rule-based processing.
- Completed:
  - Added `pyproject.toml`
  - Added source modules under `src/opspilot/` for ingest, rules, NLP, pipeline, and CLI
  - Added realistic fixtures under `data/raw/` and `tests/fixtures/`
  - Added unit tests for classifier and action extractor
  - Added integration test for full vertical slice
  - Updated `README.md` run/test guidance
- Review note: Schema validation hardening, structured logging, and richer error handling are planned for the next hardening pass.
- Next: Commit Commit 3 files and validate sample outputs for portfolio screenshots.

- Date: 2026-05-29
- Status: Commit 4 implemented
- Summary: Hardened schema validation, structured logging, and user-facing error handling across loader, pipeline, and CLI.
- Completed:
  - Added explicit OpsPilot exception hierarchy and raw-item schema validators in `src/opspilot/models/schemas.py`
  - Hardened JSON/file/read validation in `src/opspilot/ingest/loader.py`
  - Added structured logging helpers in `src/opspilot/utils/logging_utils.py`
  - Added pipeline lifecycle/failure logging and orchestration error boundary in `src/opspilot/pipeline/run_daily_ops.py`
  - Added CLI failure handling with deterministic non-zero exit code in `src/opspilot/cli.py`
  - Added unit tests for loader validation and CLI validation-failure behavior
  - Updated changelog and architecture decisions to document hardening decisions
- Next: Add reasoning traces to triage output for explainability milestone work.

- Date: 2026-05-29
- Status: Commit 5 implemented
- Summary: Added deterministic explainability reasons in triage output and improved Top Priorities readability in daily briefing.
- Completed:
  - Added `urgency_reason`, `category_reason`, and `sentiment_reason` to `TriageRecord` in `src/opspilot/models/schemas.py`
  - Refactored `src/opspilot/rules/triage_rules.py` to produce deterministic label reasons from first token match or explicit fallback reasons
  - Updated `src/opspilot/nlp/briefing_generator.py` to render Top Priorities as `ID: title`
  - Updated `src/opspilot/pipeline/run_daily_ops.py` to pass normalized work item context into briefing generation
  - Updated classifier unit tests and vertical slice integration test for new explainability and briefing format expectations
  - Updated `README.md` and `CHANGELOG.md` to document explainability and briefing quality improvements
- Next: Expand explainability traces into richer briefing sections for Milestone 2 quality goals.

- Date: 2026-05-29
- Status: Commit 6 completed
- Summary: README and documentation polish for recruiter/demo use.
- Completed:
  - Rewrote `README.md` with recruiter-friendly intro, how it works, architecture diagram, sample outputs, design decisions, and roadmap
  - No code changes
- Next: Add API layer (Commit 7)

- Date: 2026-05-29
- Status: Commit 7 implemented
- Summary: Added FastAPI-based local API service and endpoints for health, pipeline run, and output retrieval.
- Completed:
  - Added `src/opspilot/api/main.py` (FastAPI app)
  - Added API endpoints: `/health`, `/run`, `/briefing`, `/triage`
  - OpenAPI/Swagger docs auto-generated
  - API calls into existing pipeline, no business logic duplication
  - File-based storage, no DB
  - Added API tests in `tests/api/test_api.py`
  - Updated `README.md` (API usage, endpoints, Swagger UI)
  - Updated `pyproject.toml` (FastAPI/uvicorn dev dependencies)
- Next: Plan Milestone 8 (optional: authentication, error handling, or dashboard UI)

---

## Restart Handoff (Current State)

- Branch: `main`
- Latest commit: `3e008df` (`feat(api): add local FastAPI layer with health, run, and output endpoints`)
- Current capabilities:
  - Local CLI pipeline for ingest, normalization, triage, action extraction, response drafting, and briefing generation
  - Local FastAPI endpoints: `/health`, `/run`, `/briefing`, `/triage`
  - Explainable triage outputs with deterministic reason fields
- Test status:
  - `pytest -q` => `19 passed` (includes API, integration, and unit tests)
- Known issues fixed in this pass:
  - `/triage` now returns parsed JSON payload instead of raw JSON string
  - `/run` now uses explicit date contract (validation at API boundary) to avoid avoidable 500s
  - `/run` now uses current Python interpreter (`sys.executable`) for subprocess execution
  - `input_file` path traversal blocked for `/run` (`../` and nested paths rejected)
  - README duplicate/stale sections removed and wording aligned to CLI + local API
- Security rules:
  - Local-only operation
  - No cloud services, external APIs, auth systems, databases, or secrets
  - No API keys/tokens in code, tests, or docs
- Next recommended action:
  - Create a small follow-up commit for this hardening pass, then optionally add stricter API error-path coverage (still local-only)

---

## Hardening Pass: API Reliability & Safe Errors (2026-05-29)

- Summary:
  - Added subprocess timeout handling for `/run` to prevent indefinite hangs.
  - Replaced raw stderr exposure with safe structured API errors.
  - Kept useful internal error details in logs.
  - Moved FastAPI/Uvicorn to runtime dependencies for clean API installation.
  - Expanded API tests for timeout, subprocess failure, invalid date format, and safe error response shape.
- Files changed:
  - `src/opspilot/api/main.py`
  - `tests/api/test_api.py`
  - `pyproject.toml`
  - `README.md`
  - `CHANGELOG.md`
- Validation:
  - `pytest -q` (post-change) passes.
- Security stance (unchanged):
  - Local-only
  - No cloud/external APIs/auth/databases/secrets
- Next recommended action:
  - Keep this pass focused and commit as a single reliability/security hardening change set.

---

## Milestone 8: OpsPilot Command Center UI (2026-05-29)

- Summary:
  - Added a separate React + Vite + TypeScript frontend in `frontend/`.
  - Implemented dark-mode-first local command center UI with three routes:
    - Dashboard
    - Triage Explorer
    - Executive Briefing
  - Added global local-API availability banner and header health indicator via `GET /health`.
  - Added typed API client for `GET /health`, `GET /triage`, and `GET /briefing` with safe error handling.
  - Added KPI cards, top-priority panel, urgency distribution visual, triage filters, and explainability drawer.
  - Added frontend configuration template with `VITE_API_BASE_URL` defaulting to `http://127.0.0.1:8000`.
- Scope constraints honored:
  - Local-only UI
  - Read-only flow
  - No auth, database, cloud deployment, or new backend endpoints
  - No `POST /run` button in the UI

---

## Automation Phase 1A: Immutable Run History (2026-05-29)

- Summary:
  - Added immutable local run-history artifacts while preserving latest output behavior.
  - Each successful run now writes to `data/history/runs/YYYY/MM/DD/run-YYYYMMDD-HHMMSS-sss/`.
  - Latest files under `data/output/` remain unchanged for backward compatibility.
- Completed:
  - Added `src/opspilot/history/run_history.py`
  - Updated `src/opspilot/pipeline/run_daily_ops.py` to write run-history artifacts and `run.json`
  - Added integration tests for history folder creation, metadata fields, uniqueness across runs, and latest-output compatibility

## Automation Phase 1B: Run History API (2026-05-29)

- Summary:
  - Added read-only local run-history API support.
- Completed:
  - Added endpoints in `src/opspilot/api/main.py`:
    - `GET /runs`
    - `GET /runs/{run_id}`
    - `GET /runs/{run_id}/triage`
    - `GET /runs/{run_id}/briefing`
  - Added history read helpers in `src/opspilot/history/run_history.py`
  - Expanded `tests/api/test_api.py` for empty-history behavior, ordering, unknown IDs, and traversal-like IDs

## Automation Phase 1C: Frontend Historical Snapshot View (2026-05-29)

- Summary:
  - Added run-history-aware frontend behavior while preserving default Latest mode.
- Completed:
  - Added shared run selector and run status badge in app header
  - Added dashboard run history panel
  - Added historical mode selection via `?run_id=`
  - Updated Dashboard, Triage Explorer, and Executive Briefing to support latest and historical endpoints
  - Added run metadata/types and run-history API client helpers in `frontend/src/api/`

## Automation Phase 1D: Documentation Sync (2026-05-30)

- Summary:
  - Updated repository documentation to match implemented run-history storage, API endpoints, and frontend latest/historical behavior.
  - Added local scheduling design notes and explicitly marked scheduling as not yet implemented.
