# Demo Walkthrough

## Audience And Goal

Audience: recruiters and senior engineers.
Goal: show practical AI operations value with deterministic, local execution.

## Demo Length

3 to 5 minutes.

## Demo Story

1. Problem
- Teams receive mixed inbound work with unclear priorities.

2. Input
- Show local fixture with emails, tasks, and support requests.

3. Run
- Execute one CLI command for full triage pipeline.
- Start local API and frontend command center.

4. Command Center UI
- Start on Dashboard and show KPI cards plus top priorities.
- Show run selector in header with default Latest mode.
- Open run history on Dashboard and select a historical run.
- Open Triage Explorer and click a row to show explainability reasons.
- Open Executive Briefing page and show leadership-readable summary sections.
- Confirm historical run context is reflected consistently across all three pages.

5. Output Traceability
- Tie UI values back to local API and output files.
- Show immutable run folder under `data/history/runs/YYYY/MM/DD/run-...`.
- Confirm no external service calls are required.

6. Engineering Quality
- Highlight deterministic behavior and test coverage.
- Highlight decision log and milestone acceptance criteria.

7. Forward Path
- Explain how adapter seam enables future model providers without rewriting orchestration.

## Reproducible Demo Commands

From repository root:

```powershell
python -m opspilot.cli run --input data/raw/sample_input.json --output data/output --date 2026-05-30
uv run uvicorn opspilot.api.app:app --app-dir src --reload --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Optional validation before recording demo:

```powershell
pytest -q
cd frontend
npm run lint
npm run build
npm run test -- --run
```

## Demo Recording Checklist (3 to 5 minutes)

Show this sequence:

1. Project purpose in one sentence: local deterministic ops triage to executive briefing.
2. Scope guardrails: local-first, no secrets, no external APIs required.
3. Run pipeline once (or show an existing fresh output run) from local fixture data.
4. Show API surface quickly (`/health`, `/triage`, `/briefing`, `/runs`).
5. Dashboard: KPI cards and top priorities.
6. Triage Explorer: open explainability drawer to show reason fields.
7. Executive Briefing: highlight priority sections and trend/delta context.
8. Run history: switch Latest vs Historical context.
9. Engineering quality proof: show passing tests/CI checks.

Do not claim these are implemented today:

- Cloud deployment
- Authentication/authorization
- Database-backed persistence
- External AI/LLM inference calls
- Real email ingestion or notification sending

## Reviewer Checklist

A reviewer should be able to verify:

- Local run succeeds without external services.
- Outputs are understandable and operationally useful.
- Project has clear governance, scope, and decision discipline.
- Reviewer can switch between Latest and a Historical run without changing backend configuration.
- Reviewer can verify local-only scope with no cloud/auth/database/external AI dependencies.
