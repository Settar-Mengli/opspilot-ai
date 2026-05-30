# OpsPilot Command Center Frontend

This folder contains the local OpsPilot Command Center UI built with React + TypeScript + Vite.

The UI is read-only and visualizes pipeline outputs from the local FastAPI backend:
- Dashboard
- Triage Explorer
- Executive Briefing

## Local Run

1. Start API from repository root:

```sh
uvicorn opspilot.api.main:app --reload
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
