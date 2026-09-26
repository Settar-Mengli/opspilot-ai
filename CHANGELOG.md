# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog,
and this project follows Semantic Versioning principles for release tags.

## [Unreleased]

### Added

- **B1.5a UI safety net:** Playwright 1.55 visual/e2e/axe (container-only `-linux` baselines + Google WOFF2 fixtures); CI UI Tests job; CSS partials; `useOverlay`/`PortalOverlay`; U4 hygiene (subject_or_title, Connections gear label, CSS token aliases, triage/evening errors, safe-area, Sample badges); F-06 importer path jail; deprecate `opspilot.api.main`; ADRs D-026/D-027; PART 4.
- **B1 hermetic foundation:** `OPSPILOT_FORCE_RULES` + pytest-socket; uv lock / Python 3.13 / PEP 735; Compose+CI Postgres; **sync** SQLAlchemy/Alembic (`0002` `runs.finished_at` index); X5 importer; `/api/v1` Postgres-only runs (CLI `--output` files only); error envelope; AI-05 lite `subject_or_title`; Settings without `api_key_preview`; FE `/api/v1` + TS strict + vitest; gitleaks **v8.30.1** + Dependabot; pre-commit; coverage fail-under **72** (CI TOTAL 74.84%); Node 24; PART 3 + D-010/D-025 revised.
- **B0 docs lock + fix pass:** session history, audit corpus, master record PART 0–2, ADRs D-001–D-024, architecture CURRENT/TARGET, ROADMAP B0–B7, AGENTS plan gate, runbooks (local-dev, zero-spend, free-tier, GHA morning, OAuth re-auth), glossary updates.
- Session 3 (already on main): provider seam; frontend settings; SettingsPage lint fix.

### Changed

- Settings are env-only / read-only UI (PATCH removed). Coverage ratchet-only from 67.
- Roadmap IDs are **B0–B7** (+ **B1.5a/b** UI batches); owner decisions D1–D12 corrected in master record; B6 morning job in-runner (D-011); package layout D-024.
- X8 panel lifecycle started in B1.5a; agent surfaces finish on B1.5b layout in B5.

### Fixed

- V6 briefing adapter uses `subject_or_title`.
- Changelog no longer claims a shipped frontend unit/component test suite prior to B1 (Vitest smoke added in B1).

---

## Prior Unreleased (restored from main)

### Added

- Repository trust and governance foundation files.
- Initial CI skeleton workflow for basic repository validation on push and pull requests.
- Hardened input schema validation for loader-level JSON and field-shape checks.
- Structured logging helpers and pipeline lifecycle logging events.
- User-facing CLI error handling with deterministic exit code for recoverable failures.
- Unit tests for loader validation and CLI failure behavior.
- Deterministic `urgency_reason`, `category_reason`, and `sentiment_reason` fields in triage output.
- Improved executive briefing Top Priorities formatting to include item ID and title.
- Updated unit and integration tests for explainability output and briefing formatting.
- FastAPI-based local API layer (`src/opspilot/api/main.py`)
- Endpoints: `/health`, `/run`, `/briefing`, `/triage`
- OpenAPI/Swagger docs
- API tests (`tests/api/test_api.py`)
- Updated README with API usage and endpoints
- React + Vite + TypeScript frontend in `frontend/` for local command center experience
- Command center routes: Dashboard, Triage Explorer, Executive Briefing
- Header health indicator and global API unavailable banner based on `GET /health`
- Explainability drawer in triage explorer showing urgency/category/sentiment reasons
- Frontend env template `frontend/.env.example` for `VITE_API_BASE_URL`
- Immutable local run-history artifacts under `data/history/runs/YYYY/MM/DD/run-YYYYMMDD-HHMMSS-sss/`
- Run metadata artifact `run.json` per successful run
- Run-history API endpoints:
	- `GET /runs`
	- `GET /runs/{run_id}`
	- `GET /runs/{run_id}/triage`
	- `GET /runs/{run_id}/briefing`
- Frontend historical snapshot support via shared run selector and `?run_id=` query parameter
- Dashboard run history panel and latest/historical status context badge
- Executive Briefing "Since Last Run" delta section comparing priority counts (`critical`, `high`, `medium`, `low`) to the immediately previous run
- Executive Briefing "Recent Trend (Last 7 Runs)" section summarizing deterministic high-risk (`critical + high`) counts and net change
- Vitest + Testing Library installed as FE tooling baseline (no \*.test.*\ / \*.spec.*\ under \rontend/src\ as of HEAD !a8678\ — prior changelog overstated a shipped FE test suite)
- API tests for metadata allow-listing and artifact-name edge-case handling
- API tests for local-origin CORS preflight behavior

### Changed

- Hardened API run contract in `src/opspilot/api/main.py`:
	- `date` is validated by API request schema
	- subprocess execution uses `sys.executable`
	- `input_file` is restricted to filenames under `data/raw`
	- subprocess execution now has a bounded timeout for reliability
- `/triage` now returns parsed JSON payloads instead of raw JSON strings
- `/run` now returns safe structured error payloads and avoids exposing raw stderr to clients
- Strengthened API tests in `tests/api/test_api.py` for JSON shape, timeout handling, subprocess failure behavior, and invalid date input
- Cleaned duplicated/stale sections in `README.md` and aligned wording to CLI + local API
- Added a short Security & Reliability section to `README.md`
- Added explicit restart handoff section to `PROGRESS.md`
- Moved `fastapi` and `uvicorn[standard]` to runtime dependencies in `pyproject.toml`
- Expanded README run instructions to include local frontend startup and API/UI flow
- Updated architecture and demo docs to include command center UI walkthrough
- Pipeline now writes immutable run artifacts while preserving latest-output compatibility in `data/output/`
- Frontend pages now support both Latest and Historical run contexts without adding new routes
- Briefing delta markers now use ASCII-only output for terminal compatibility:
	- `0` for no change
	- `+N` for increase
	- `-N` for decrease
- CI workflow now runs backend `pytest -q` and frontend `npm ci`, `npm run lint`, and `npm run build` on push and pull request
- Run-history metadata API responses now sanitize `input_file`, `output_dir`, and `history_dir` for `GET /runs` and `GET /runs/{run_id}`
- Expanded API metadata safety tests to assert sanitized fields are excluded and artifact names remain path-safe
- Added API test coverage to reject traversal-like run IDs for `GET /runs/{run_id}` metadata endpoint
- Run-history metadata responses now use explicit allow-listed key shaping at API boundary
- Artifact names in metadata responses now drop invalid/path-like/empty/unexpected values defensively
- CORS policy now explicitly allows `GET` and `POST` for local UI origins only, with credentials disabled
- README and docs now include local-first security checklist, reproducible validation flow, scheduling status clarity, and roadmap-only integration notes
- `.gitignore` now includes frontend generated artifacts and local runtime log hygiene
