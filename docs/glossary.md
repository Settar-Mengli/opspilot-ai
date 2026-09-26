# Glossary

## Core Entities

- Work Item: A normalized unit of inbound work from email, task, or support request sources.
- Triage Record: The structured classification output for one work item.
- Executive Briefing: Daily summary intended for a leadership readout.

## Classification Terms

- Urgency: Priority level for response timing.
- Category: Work type grouping used for routing and response style.
- Sentiment: Tone signal inferred from item content.

## Approved Label Sets (Milestone 1)

- Urgency: low, medium, high, critical
- Category: incident, request, admin, follow_up, other
- Sentiment: negative, neutral, positive

## Extraction Terms

- Action Item: A concrete next step inferred from content.
- Owner: Suggested responsible person or team.
- Deadline: Date or time constraint found in text.
- Explicit Ask: Direct requested action stated in the item.

## Workflow Terms

- Vertical Slice: End-to-end thin implementation proving real execution.
- Deterministic: Same input produces the same output.
- Adapter Seam: Interface boundary allowing provider swaps without orchestration changes.

## Scope Terms

- Local-Only: All processing occurs on the developer machine without external service calls.
- Non-Authoritative AI Memory: Supplemental notes that cannot override project decisions.

## Rebuild Terms (B0+)

- CURRENT: Fact verified in code or audit evidence at a named HEAD.
- TARGET: Planned architecture/behavior not yet shipped.
- Batch (B0–B7): Locked delivery unit; may contain former M* workstreams.
- ADR: Architecture Decision Record under `docs/adr/`.
- Gateway: Hand-rolled LLM routing/metering/budget choke point (D-012).
- Hermetic: Tests that do not call live LLMs or depend on ambient `.env` keys / shared `data/output`.
- DEMO_MODE: Visitor-safe mode; blocks send and operator-only actions.
- Neon: Hosted Postgres provider chosen for TARGET persistence (D-008).
- Prepaid Anthropic gate: Opt-in allowlist + token/USD budget; never default/tests/CI (D-023).
- LlmCall: Persisted metering row for tokens/latency/cost accounting.
