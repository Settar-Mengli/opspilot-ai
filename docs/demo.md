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
- Open Triage Explorer and click a row to show explainability reasons.
- Open Executive Briefing page and show leadership-readable summary sections.

5. Output Traceability
- Tie UI values back to local API and output files.
- Confirm no external service calls are required.

6. Engineering Quality
- Highlight deterministic behavior and test coverage.
- Highlight decision log and milestone acceptance criteria.

7. Forward Path
- Explain how adapter seam enables future model providers without rewriting orchestration.

## Reviewer Checklist

A reviewer should be able to verify:

- Local run succeeds without external services.
- Outputs are understandable and operationally useful.
- Project has clear governance, scope, and decision discipline.
