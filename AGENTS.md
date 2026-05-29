# AGENTS

This file defines operating rules for Copilot-assisted and human development in this repository.

## Core Workflow Rules

1. Explain before edit.
2. Keep changes small and reviewable.
3. Do not implement outside approved scope.
4. After each coding step, produce an implementation report.

## Required Implementation Report (After Each Step)

- What changed
- Files created/edited
- How to run
- How to test
- Recommendations for improvement

## Testing Expectations

- Any behavior change must include tests or a written reason for deferral.
- Prefer deterministic tests over flaky heuristics.
- Validate relevant tests before closing a step.

## Safe Git Behavior

- Never use destructive commands such as `git reset --hard` unless explicitly requested.
- Never revert unrelated user changes.
- Keep commits focused on one intent.

## Documentation Discipline

- Update `PROGRESS.md` for every completed step.
- Record significant architectural decisions in `docs/decisions.md` once docs are created.

## Scope Constraints

- Local-only development
- No paid API dependency
- No real external service integrations in early milestones
