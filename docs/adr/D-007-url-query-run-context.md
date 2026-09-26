# D-007: URL Query Param As Frontend Run Context

- **Date:** 2026-05-29
- **Status:** Accepted
- **Blocks:** —

## Context

Frontend needed to switch between latest and historical snapshots without complex state infrastructure.

## Decision

Use ?run_id= as shared run context across Dashboard, Triage Explorer, and Executive Briefing.

## Alternatives considered

localStorage-only context; dedicated run-history route before proving UX value.

## Options

| Option | Tradeoffs |
|--------|-----------|
| (a) \?run_id=\ | Deep-linkable; simple |
| (b) localStorage-only | No shareable links |

## Acceptance criteria

- FE continues to support latest vs historical via un_id\ (or \/api/v1\ equivalent) with graceful invalid-ID fallback.

## Consequences

Simple deep-linkable behavior; invalid run IDs require graceful fallback UX.
