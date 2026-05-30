# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog,
and this project follows Semantic Versioning principles for release tags.

## [Unreleased]


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
