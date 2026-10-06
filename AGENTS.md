# AGENTS

Operating rules for AI-assisted and human development in this repository.

## Grounding

> Ground every decision in what the repo actually is. Record facts as CURRENT only when verified in code; label everything planned as TARGET. Recommend, record, and build like a production engineer — no padding, no aspirational claims presented as fact.

Canonical plan: [OPSPILOT-MASTER-RECORD.md](OPSPILOT-MASTER-RECORD.md) · [ROADMAP.md](ROADMAP.md) (B0–B6 + backlog B7; see ROADMAP / PART 21) · [docs/architecture.md](docs/architecture.md) · [docs/adr/](docs/adr/)

### Source of truth

When documents conflict, follow these as authoritative:

- ADRs under [`docs/adr/`](docs/adr/) **including Status headers and addenda**
- [`OPSPILOT-MASTER-RECORD.md`](OPSPILOT-MASTER-RECORD.md) PARTs
- [`ROADMAP.md`](ROADMAP.md)
- [`docs/audits/2026-09-30-consolidated-audit.md`](docs/audits/2026-09-30-consolidated-audit.md) (decision register + B3 locks)

Treat as **historical records only** (do not follow as instructions where they conflict):

- `docs/audits/*` older than `2026-09-30-*`
- `docs/history/*`

Do not rewrite historical audits or history files to “fix” drift; update ADRs (status/addenda), ROADMAP, CURRENT docs, or append a master-record PART instead.

### Single source-of-truth rules (recurring facts)

| Fact | Authoritative home | Other docs |
|------|--------------------|------------|
| Batch status / next batch | [ROADMAP.md](ROADMAP.md) | README one-liner links ROADMAP; PARTs record events |
| Merge SHAs / PR # / CI run ids | [OPSPILOT-MASTER-RECORD.md](OPSPILOT-MASTER-RECORD.md) PART for that batch | CHANGELOG may cite once |
| Live eval numbers / n / partial days | [docs/evals/leaderboard.md](docs/evals/leaderboard.md) + `docs/evals/results/*.json` | README/architecture link only |
| Model ids (code fallbacks) | `src/opspilot/llm/model_defaults.py` | `.env.example` + [docs/runbooks/llm-providers.md](docs/runbooks/llm-providers.md) must match |
| Budget caps / env names | `.env.example` + [docs/runbooks/llm-providers.md](docs/runbooks/llm-providers.md) | `budgets.py` reads env only |
| Alembic head | `alembic/versions/` (highest) + PART when applied to Neon | architecture cites head |
| API surface | OpenAPI / `src/opspilot/api/v1/` | [docs/architecture.md](docs/architecture.md) CURRENT endpoint table |
| Node version | `.nvmrc` + CI `node-version` + `frontend/package.json` engines | README states ≥24.15 |
| Python version | `pyproject.toml` `requires-python` | README / architecture cite 3.13 |
| Coverage gate | CI `--cov-fail-under=72` | PARTs may record measured TOTAL |
| Test count | CI / local `pytest` for a named SHA | PART append only |
| ADR status | Each ADR header + addenda | [docs/adr/README.md](docs/adr/README.md); design-decisions = short links |
| Zero-spend / Anthropic | this file + D-023 | Runbooks link; leaderboard says skipped |

## Zero-spend

1. No further paid API purchase.
2. Default LLM path = free tiers + Ollama + rules — **never** Anthropic by default.
3. Anthropic only via existing prepaid credits, allowlisted tasks (`ask`/`triage`), and gateway **token + USD** prepaid ledger (D-023). Operator Ask SSE + Sync drain triage under `OperatorAnthropicAuth` when ENABLED (off by default). Never in tests/CI. Never for visitor Ask (D2 / D11).
4. GitHub MCP (`OPSPILOT_GITHUB_MCP_ENABLED`, `GITHUB_MCP_PAT`, owner/repo env **names** only) is off by default, operator-local, never CI, never a paid Copilot purchase (D-034 / L12). Never print PAT values.
5. Fictional demo data only; Google OAuth stays Testing; visitors never connect Gmail.
6. Do not invent quota numbers — VERIFY AT DECISION TIME.
7. **Never print secrets** (`.env` values, API keys, refresh tokens) in chat, logs, commits, or docs.
8. **DEMO_MODE:** visitors cannot send mail or perform operator-only actions.

## X4 — Prompt / data minimization

Free tiers (e.g. Gemini unpaid) **may train on prompts**. Minimize sensitive content in prompts; use fictional data; prefer local/Ollama for anything that must not leave the machine. Do not confuse X4 with “hide secrets in docs” — secrets stay out of docs and chat under the separate never-print-secrets rule.

## Hermetic tests

- Default pytest suite must not call live LLMs.
- Prefer fakes/tmp dirs; no reliance on repo `data/output` order.
- If a key is present in `.env`, tests must still not spend (network-blocking fixture in B1).

## Batch workflow (mandatory)

1. **Plan mode:** every batch is planned as **ONE large batch**. Build only after **owner confirmation**.
2. **Build:** implement the approved batch; prefer small reviewable commits **inside** the batch; each commit leaves tests green.
3. After Build: **Ask-mode audit** → one **Agent fix pass** that commits, pushes, and **opens the PR**.
4. **Branching:** one branch per batch (`bN/...`) cut from updated `main`. Agent commits and pushes; **NEVER merges**. Operator merges after CI is green.
5. **Live smoke** with exact commands before opening/updating the PR.
6. **Docs every batch:** append a master-record PART (after main merge rule applies); update ROADMAP / ADRs / CHANGELOG / docs.
7. Do not pull CUT-list items without an explicit owner decision; DEFER items need a trigger.
8. **One commit per push:** never batch multiple commits into one push. Push each commit alone, wait for full CI green (including UI Tests) on that SHA, then make the next commit. No force-push to rewrite a red SHA — fix forward.

## Plan requirements

Every batch plan must show:

1. Scope equals exactly the ROADMAP batch — nothing missing, no cut-list items.
2. Conformance to locked decisions/ADRs; any deviation requires a new or updated ADR in the same batch.
3. Concrete, measurable exit criteria (exact commands and thresholds; no soft wording that defers a gate without a number).
4. A commit sequence where each commit leaves tests green.
5. Zero-spend and hermetic: no paid calls, no live LLM in tests/CI, never print secrets, never modify `.env`.
6. Data safety: reversible migrations; no destructive git.
7. Live smoke with exact commands.
8. Docs: master-record PART appended; ROADMAP / ADRs / CHANGELOG updated.
9. Risks and rollback.
10. Claims verified against the actual code with path:line references.

## Testing

- Behavior changes need tests or a written deferral reason.
- Prefer deterministic tests over flaky heuristics.
- Validate relevant tests before closing a step.
- **Before every commit:** run `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src/opspilot`, and `uv run pytest -q`. Never push a commit that fails them. Install hooks once with `uv run pre-commit install`.

## UI safety net (D-026)

- Visual baselines are **container-only** (`mcr.microsoft.com/playwright` pin; filenames end in `-linux`). Host visual runs are unsupported; host may run e2e/axe only. See [docs/runbooks/ui-tests.md](docs/runbooks/ui-tests.md).
- Any **375** baseline change needs owner approval in the PR + visual sign-off.
- Behavior-only FE changes must keep `maxDiffPixels: 0` at all viewports unless the commit names the U4/OD states being updated, or updates an owner-approved per-state entry in `frontend/e2e/visual.spec.ts` (`MAX_DIFF_PIXELS`; changing any entry requires owner approval).
- Contrast/focus-ring pixel fixes are separate ODs — do not auto-apply.

## Safe git

- No destructive commands (`git reset --hard`, force-push to main) unless explicitly requested.
- Never revert unrelated user changes.
- Commits focused on one intent.
- Agent never merges to `main`.

## Documentation

- Update the master record / ROADMAP / ADRs when decisions change — **not** a separate PROGRESS.md (retired in B0).
- After merge to `main`, master-record PARTs are append-only.

## Scope constraints (early batches)

- Local-only until the batch that introduces the integration
- No paid API dependency
- No real external service integrations before their locked batch (B4+)
- No public backend planned (B7 dropped — PART 21). Local API stays on `127.0.0.1`. B6 morning job in-runner (D-011)
