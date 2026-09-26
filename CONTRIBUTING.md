# Contributing

Thanks for contributing to OpsPilot AI.

## Principles

- Keep changes scoped and purposeful.
- Prefer deterministic, testable behavior.
- Distinguish CURRENT (verified) from TARGET (planned).
- Update docs when behavior or process changes.
- Follow [AGENTS.md](AGENTS.md) (zero-spend, hermetic tests, cut-list discipline).

## Workflow (Ask → Plan → Build)

1. **Ask** — read-only analysis; no file writes.
2. **Plan** — owner-approved plan before implementation.
3. **Build** — implement only the approved step; report; stop for review.

Explain before edit. Small reviewable diffs. Implementation report after each step.

## Branch naming

**Preferred for roadmap work:** one branch per batch:

- `b0/docs-architecture-lock`
- `b1/...`, `b2/...`, …

Also acceptable for small fixes:

- `feat/<short-topic>` · `fix/<short-topic>` · `docs/<short-topic>` · `chore/<short-topic>` · `test/<short-topic>`

## Commit messages

Conventional Commits:

- `feat:` · `fix:` · `docs:` · `test:` · `chore:`

## Pull requests

- One intent per PR.
- Include testing notes and a short implementation report (what / run / test / follow-ups).
- Do not merge CUT-list or out-of-batch scope without an explicit decision.

## Local validation (typical)

```powershell
.venv\Scripts\python -m pytest -q
cd frontend; npm run lint; npm run build
```

Key check (True/False only — never print secrets):

```powershell
(Select-String -Path .env -Pattern '^\s*(ANTHROPIC_API_KEY|OPSPILOT_AI_API_KEY)\s*=\s*\S' -Quiet)
```

Expect **False** during zero-spend hermetic work unless running an explicit budgeted operator script.

## Documentation sources of truth

| Topic | File |
|-------|------|
| Locked plan | `OPSPILOT-MASTER-RECORD.md` |
| Batches B0–B7 | `ROADMAP.md` |
| CURRENT vs TARGET architecture | `docs/architecture.md` |
| Decisions | `docs/adr/` |
| Agent rules | `AGENTS.md` |
| Runbooks | `docs/runbooks/` |
