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

Commit 1 establishes repository trust/governance and CI skeleton.

Next milestone: build a runnable vertical slice that ingests sample JSON, classifies items, extracts actions, drafts responses, and generates a daily briefing.

## Planned Repository Areas

- `.github/workflows/` for CI
- `data/` for local fixtures and outputs
- `src/` for Python application code (created in next commit)
- `tests/` for unit and integration tests (created in next commit)

## License

MIT (see `LICENSE`).
