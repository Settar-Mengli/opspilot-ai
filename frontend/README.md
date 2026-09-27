# OpsPilot Command Center Frontend

This folder contains the local OpsPilot Command Center UI built with React + TypeScript + Vite.

The UI is read-only and visualizes pipeline outputs from the local FastAPI backend:
- Dashboard
- Triage Explorer
- Executive Briefing

The UI supports two contexts:
- Latest mode (default)
- Historical mode via `?run_id=<run-id>`

## Local Run

1. Start API from repository root:

```sh
uv run uvicorn opspilot.api.app:app --app-dir src --reload --host 127.0.0.1 --port 8000
```

2. In a new terminal, start UI:

```sh
cd frontend
npm install
npm run dev
```

## API Base URL

- Configure with `VITE_API_BASE_URL` (see `.env.example`).
- Default fallback is `http://127.0.0.1:8000`.
- For local-first safety, only `localhost` and `127.0.0.1` origins are accepted.
- Invalid or remote origins are rejected and safely fall back to `http://127.0.0.1:8000`.

## Run History Behavior

- Header run selector loads run metadata from `GET /runs`.
- Latest mode uses:
	- `GET /triage`
	- `GET /briefing`
- Historical mode uses:
	- `GET /runs/{run_id}/triage`
	- `GET /runs/{run_id}/briefing`
- Dashboard, Triage Explorer, and Executive Briefing are all run-context aware.
- Selecting Latest removes `run_id` from the URL query.
- If no history exists, the UI remains functional in Latest mode.

## Build

```sh
cd frontend
npm run build
```

## Local-Only Security Notes

- No cloud services
- No authentication
- No database
- No deployment configuration
- No AI/LLM calls in frontend

## Portfolio Review Alignment

- For reviewer-facing quickstart, screenshot guidance, and end-to-end demo flow, use the root README and `docs/demo.md`.
