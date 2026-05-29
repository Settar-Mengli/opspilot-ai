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
