# OpsPilot AI

OpsPilot AI is a local AI operations command center that simulates how an assistant triages incoming work from emails, tasks, and support requests.

## Vision

Turn noisy operational inputs into clear priorities, action items, suggested responses, and a concise daily executive briefing.

## Local-Only Constraints

- Local development only
- No paid API keys
- No real Gmail/Calendar integrations yet
- Python-first implementation
- Rule-based AI simulation first

## Why This Repository Exists

This project is designed as a portfolio-quality example of practical AI product engineering:

- Deterministic classification and extraction pipeline
- Clear governance and decision-making process
- Test-first, maintainable development workflow

## Current Status

Commit 3 delivers the first runnable vertical slice.

Current capabilities:

- Read local JSON work items
- Normalize Work Items
- Classify Urgency, Category, and Sentiment
- Extract Action Items
- Draft suggested responses
- Generate an Executive Briefing and structured output artifacts

## Setup

From project root in PowerShell:

1. `python -m venv .venv`
2. `.venv\Scripts\Activate.ps1`
3. `pip install -e .[dev]`

## Run

`python -m opspilot.cli run --input data/raw/sample_input.json --output data/output --date 2026-05-29`

## Test

`pytest -q`

## Expected Output Files

- `data/output/triage_results.json`
- `data/output/action_items.json`
- `data/output/suggested_responses.json`
- `data/output/daily_briefing.txt`

## Planned Repository Areas

- `.github/workflows/` for CI
- `data/` for local fixtures and outputs
- `src/` for Python application code
- `tests/` for unit and integration tests

## License

MIT (see `LICENSE`).
