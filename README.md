
# OpsPilot AI

**From noisy inbox to clear priorities in minutes.**

OpsPilot AI is a local, rule-based operations command center that simulates how an assistant triages and summarizes incoming work (emails, tasks, support requests). It turns unstructured signals into prioritized action items, suggested responses, and a daily executive briefing—entirely offline, with no paid APIs or secrets required.

---

## How it works

1. **Ingest**: Reads local JSON files with mock emails, tasks, and support tickets.
2. **Normalize**: Converts each item to a unified internal format.
3. **Classify**: Assigns urgency, category, and sentiment using deterministic rules.
4. **Explain**: Captures the exact rule or token that triggered each label.
5. **Extract Actions**: Finds deadlines, owners, and explicit asks.
6. **Draft Responses**: Suggests a reply template for each item.
7. **Briefing**: Generates a daily executive summary with top priorities, due-soon action items, and a "Since Last Run" priority delta section when a prior run exists.

---

## Architecture

```mermaid
flowchart TD
		A[Input JSON emails tasks support] --> B[Ingest Normalize]
		B --> C[Rule-based Classifier]
		C --> D[Action Extractor]
		C --> E[Suggested Response Drafter]
		D --> F[Briefing Generator]
		E --> F
		C --> G[Triage Output]
		D --> H[Action Items Output]
		E --> I[Suggested Responses Output]
		F --> J[Daily Briefing Output]
		K[FastAPI Local API health triage briefing] --> L[React Command Center UI]
		G --> K
		J --> K
```

---

## Sample Output

**Triage Record (JSON):**
```json
{
	"id": "WI-001",
	"urgency": "critical",
	"urgency_reason": "Matched critical token 'sev1'",
	"category": "incident",
	"category_reason": "Matched incident token 'down'",
	"sentiment": "negative",
	"sentiment_reason": "Matched negative sentiment token 'escalat'"
}
```

**Daily Briefing (text):**
```
OpsPilot AI Daily Executive Briefing - 2026-05-29

Total Work Items: 6
Urgency Mix: critical=1, high=1, medium=2, low=2
Sentiment Mix: negative=2, neutral=3, positive=1

Top Priorities:
- WI-001: Production outage in checkout service
- WI-004: Customer escalation on ticket #4032

Due-Soon Action Items:
- WI-004: Customer escalation on ticket #4032 (owner=unassigned, deadline=EOD)
```

---

## Design decisions and tradeoffs

- **Rule-based first**: Deterministic, testable, and easy to reason about for portfolio/demo use. (No LLMs or paid APIs.)
- **Local-only**: No secrets, no cloud dependencies, runs on any machine.
- **Explicit validation**: Fails fast on bad input, with clear error messages.
- **Explainability**: Every label is accompanied by a reason string for transparency.
- **CLI + local API**: Operate via command line or local FastAPI endpoints, with no cloud dependency.
- **Extensible**: Architecture is modular, with clear seams for future model or API adapters.

---

## Future roadmap

- **Milestone 2**: Add richer explainability traces and improved executive briefing quality.
- **Milestone 3**: Introduce pluggable model adapters (LLM or API-backed components).
- **Milestone 4**: Add mock connectors for future integrations (Gmail, Jira, etc.).
- **Beyond**: Optional dashboard UI, real-time event pipeline, and production deployment patterns.

---

## Setup

From project root in PowerShell:

1. `python -m venv .venv`
2. `.venv\Scripts\Activate.ps1`
3. `pip install -e .[dev]`


## Run (CLI)

```sh
python -m opspilot.cli run --input data/raw/sample_input.json --output data/output --date 2026-05-29
```

## Run (API)

Start the API server locally:

```sh
uvicorn opspilot.api.main:app --reload
```

Swagger/OpenAPI docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### API Endpoints

- `GET /health` — Health check
- `POST /run` — Run the pipeline (body: `{ "input_file": "sample_input.json", "date": "YYYY-MM-DD" }`)
- `GET /briefing` — Get latest daily briefing
- `GET /triage` — Get latest triage results
- `GET /runs` — List run-history metadata (newest first)
- `GET /runs/{run_id}` — Get metadata for a specific historical run
- `GET /runs/{run_id}/triage` — Get triage results for a specific historical run
- `GET /runs/{run_id}/briefing` — Get briefing text for a specific historical run

## Run (UI)

Start the API first in one terminal:

```sh
uvicorn opspilot.api.main:app --reload
```

In another terminal, run the frontend:

```sh
cd frontend
npm install
npm run dev
```

Frontend defaults to `http://127.0.0.1:8000` for API calls.
To override, copy `frontend/.env.example` to `.env` and set `VITE_API_BASE_URL`.

UI routes:

- Dashboard
- Triage Explorer
- Executive Briefing

Run context behavior:

- Default mode is **Latest** (no query parameter).
- Historical mode is selected with `?run_id=<run-id>`.
- In historical mode, Dashboard, Triage Explorer, and Executive Briefing render a consistent snapshot for the selected run.
- Selecting Latest removes the query parameter and returns all pages to latest endpoints.

## Security & Reliability

- Local-only architecture: no cloud services, no external APIs, no secrets.
- `/run` uses strict input filename validation to block path traversal attempts.
- `/run` uses a bounded subprocess timeout to prevent indefinite API hangs.
- API error responses are intentionally safe and structured; internal command details are logged but not exposed to clients.
- Frontend consumes only local API endpoints and uses no external network calls.

## Test

```sh
pytest -q
```

## Output files

- `data/output/triage_results.json`
- `data/output/action_items.json`
- `data/output/suggested_responses.json`
- `data/output/daily_briefing.txt`

These latest files remain the backward-compatible snapshot used by existing flows.

## Run history artifacts

Each successful run also writes immutable artifacts under:

- `data/history/runs/YYYY/MM/DD/run-YYYYMMDD-HHMMSS-sss/`

Each run folder contains:

- `run.json`
- `triage_results.json`
- `action_items.json`
- `suggested_responses.json`
- `daily_briefing.txt`

Notes:

- `data/history/` is generated local runtime data.
- `data/history/` is intentionally ignored by git and should not be committed.

## Scheduling status

- Local scheduling is **design-only** right now (not yet implemented in application code).
- See `docs/scheduling.md` for local scheduling guidance and scope-safe recommendations.

## Triage Output Fields

Each triage record includes:

- `id`
- `urgency`
- `urgency_reason`
- `category`
- `category_reason`
- `sentiment`
- `sentiment_reason`

---

## License

MIT (see `LICENSE`).
