# D-024: Target Package Layout (Principal-Review §2.1)

- **Date:** 2026-09-26
- **Status:** Accepted
- **Blocks:** B1–B7 (layout introduced progressively; tree is TARGET SoT)

## Context

B0 architecture used shorthand names (`gateway/`, `db/`) that diverge from the locked principal-review tree. Implementers need one layout. D-022 keeps top-level `src/opspilot/` + `frontend/` only.

## Options

| Option | Tradeoffs |
|--------|-----------|
| (a) Adopt principal-review §2.1 exactly | Aligns audits/ADRs; one rename pass in B1 |
| (b) Keep gateway/db shorthand | Less rename; permanent drift from review |
| (c) apps/ packages monorepo | Violates D-022 |

## Decision

**(a)** TARGET layout under `src/opspilot/`:

`api/` (app.py, deps.py, errors.py, `v1/` routes), `domain/`, `services/`, `llm/` (gateway, routing, budgets, prompts, providers), `agent/`, `integrations/`, `persistence/` (db, repositories, Alembic), `jobs/`, `evals/`, `obs/`, `config/`, `rules/`.

**Dependency rules:**

- `api` → `services` → (`domain`, `llm`, `agent`, `integrations`, `persistence`)
- `agent` → `llm` + read services; never `integrations.send` without approval service
- `evals` may use `rules` + LLM fakes; never load `.env` keys in CI lane
- `integrations` must not import `api`
- No upward imports from `llm` into `api`
- Provider SDKs only inside `llm/providers/`

## Acceptance criteria

- `docs/architecture.md` TARGET package section matches this tree and rules.
- ADR index lists D-024; no conflicting gateway/db TARGET names remain in architecture/ROADMAP.

## Consequences

B1 begins reshaping toward this tree with `/api/v1` + persistence. Legacy adapter paths migrate across B1–B2.

## Blocks

B1–B7.
