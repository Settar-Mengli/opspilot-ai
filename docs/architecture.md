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

## Planned Module Boundaries

- ingest: load and normalize input artifacts
- rules: deterministic classification logic
- nlp: extraction, response drafting, briefing composition
- pipeline: orchestration of end-to-end run
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
