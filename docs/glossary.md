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
