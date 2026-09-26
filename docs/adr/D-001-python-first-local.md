# D-001: Python-First Local Architecture

- **Date:** 2026-05-29
- **Status:** Accepted
- **Blocks:** —

## Context

The project must be beginner-friendly, local-only, and portfolio-ready.

## Decision

Use a Python-first project structure with local CLI execution.

## Alternatives considered

JavaScript-first stack; notebook-only workflow.

## Options

| Option | Tradeoffs |
|--------|-----------|
| (a) Python-first local | Fast onboarding; strong test tooling |
| (b) JS-first | Unifies FE/BE; weaker early CLI story |
| (c) Notebook-only | Poor packaging |

## Acceptance criteria

- Repo remains installable as a Python package under \src/opspilot/\.

## Consequences

Faster local onboarding, clear packaging path, easier test tooling.
