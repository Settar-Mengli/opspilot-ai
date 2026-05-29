# Milestones

## Delivery Strategy

- Keep milestones small, reviewable, and testable.
- Ship a runnable vertical slice early.
- Defer external integrations until core workflow is stable.

## Milestone 1: Rule-Based Vertical Slice

### Objective

Deliver a local CLI workflow that ingests mock JSON work items and outputs triage results plus a daily executive briefing.

### Included Scope

- Local JSON ingestion from fixture files
- Deterministic rule-based classification:
  - Urgency
  - Category
  - Sentiment
- Action item extraction
- Suggested response drafting
- Executive briefing generation
- Unit and integration tests for core flow

### Excluded Scope

- Paid API usage
- Real Gmail or Calendar integrations
- Web UI or deployment infrastructure
- Background workers or real-time event pipelines

### Acceptance Criteria (Binary)

Pass when all items below are true:

1. A single CLI command runs the full local pipeline from input file to output artifacts.
2. Each input item has exactly one urgency label from an approved set.
3. Each input item has exactly one category label from an approved set.
4. Each input item has exactly one sentiment label from an approved set.
5. Action items are produced for items that contain explicit asks or deadlines.
6. Suggested response text is produced for every processed item.
7. A human-readable daily briefing file is generated.
8. Structured machine-readable output file is generated.
9. Unit tests pass for classification and extraction modules.
10. At least one integration test passes for end-to-end pipeline execution.
11. README run/test instructions work on a clean local machine.
12. No external service calls are required to complete the run.

## Milestone 2: Explainability and Quality

- Add rationale traces for rule outcomes.
- Improve briefing quality and prioritization framing.
- Expand fixture coverage for edge cases.

## Milestone 3: Adapter-Ready Intelligence

- Introduce provider adapter interface for optional model-backed components.
- Compare rule-based and adapter-based outputs.

## Milestone 4: Integration-Ready Architecture

- Add local mock connectors for future tools.
- Keep integration boundaries explicit and testable.
