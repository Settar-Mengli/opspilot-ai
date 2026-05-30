# Architecture

## Purpose

OpsPilot AI is a local-only operations command center that transforms mock inbound work into prioritized actions and a daily briefing.

## Constraints

- Local-only development and execution
- Rule-based AI simulation first
- No paid API dependencies
- No real external integrations in Milestone 1

## System Flow

1. Ingest local JSON fixtures
2. Normalize to a common work-item structure
3. Classify each item (urgency, category, sentiment)
4. Extract action items
5. Draft suggested responses
6. Generate executive briefing and structured outputs
7. Serve read-only outputs through local FastAPI endpoints
8. Render command center UI from local API responses

## Storage Model

Latest snapshot (backward-compatible):

- `data/output/triage_results.json`
- `data/output/action_items.json`
- `data/output/suggested_responses.json`
- `data/output/daily_briefing.txt`

Immutable history snapshot (per successful run):

- `data/history/runs/YYYY/MM/DD/run-YYYYMMDD-HHMMSS-sss/`
	- `run.json`
	- `triage_results.json`
	- `action_items.json`
	- `suggested_responses.json`
	- `daily_briefing.txt`

Runtime data note:

- `data/history/` is generated local runtime data and is git-ignored.

## Planned Module Boundaries

- ingest: load and normalize input artifacts
- rules: deterministic classification logic
- nlp: extraction, response drafting, briefing composition
- pipeline: orchestration of end-to-end run
- api: local read/write orchestration boundary for run + output retrieval
- frontend: local read-only command center routes (dashboard, triage explorer, briefing)
- models: shared schemas and enums
- utils: IO and logging helpers

## Data Contracts

Input contract:
- Source types: email, task, support_request
- Required fields: id, source_type, subject_or_title, body_or_description

Output contract:
- Per-item triage record with urgency, category, sentiment
- Action extraction payload
- Suggested response text
- Daily briefing artifact

History contract:

- `run.json` stores run metadata (run_id, timestamps, status, counts, artifact names, error field)
- historical artifacts preserve deterministic snapshot outputs for auditability and demo traceability

## API Retrieval Modes

Latest mode endpoints:

- `GET /triage`
- `GET /briefing`

Historical mode endpoints:

- `GET /runs`
- `GET /runs/{run_id}`
- `GET /runs/{run_id}/triage`
- `GET /runs/{run_id}/briefing`

Frontend run selection:

- Query parameter `run_id` determines historical context.
- No `run_id` means Latest mode.

## Adapter Seam For Future Integrations

Future model integrations must be added behind adapter interfaces so core pipeline remains stable.

Adapter seam requirements:
- Stable interface for classify, extract, draft, and summarize operations
- Deterministic fallback to rule-based providers
- No direct provider calls from pipeline orchestration layer

## Error Handling Principles

- Fail fast on invalid input schema
- Continue processing valid items when isolated item-level errors occur
- Emit explicit processing status for each item

## Non-Goals For Current Phase

- Real inbox/calendar integrations
- Autonomous agent actions on external systems
- Production deployment concerns
- In-app scheduler or background scheduling daemon

## Milestone 8 UI Scope Constraints

- Local-only frontend execution
- No authentication or authorization layer
- No database persistence
- No cloud deployment setup
- No new backend endpoints required for initial command center views
