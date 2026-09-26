# AGENTS

Operating rules for AI-assisted and human development in this repository.

## Grounding

> Ground every decision in what the repo actually is. Record facts as CURRENT only when verified in code; label everything planned as TARGET. Recommend, record, and build like a production engineer — no padding, no aspirational claims presented as fact.

Canonical plan: [OPSPILOT-MASTER-RECORD.md](OPSPILOT-MASTER-RECORD.md) · [ROADMAP.md](ROADMAP.md) (B0–B7) · [docs/architecture.md](docs/architecture.md) · [docs/adr/](docs/adr/)

## Zero-spend

1. No further paid API purchase.
2. Default LLM path = free tiers + Ollama + rules — **never** Anthropic by default.
3. Anthropic only via existing prepaid credits, allowlisted tasks, and gateway **token + USD** budget (D-023). Never in tests/CI. Never for visitor Ask (D2 / D11).
4. Fictional demo data only; Google OAuth stays Testing; visitors never connect Gmail.
5. Do not invent quota numbers — VERIFY AT DECISION TIME.
6. **Never print secrets** (`.env` values, API keys, refresh tokens) in chat, logs, commits, or docs.
7. **DEMO_MODE:** visitors cannot send mail or perform operator-only actions.

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
- Public backend only at **B7** (D6); B6 morning job runs in-runner (D-011)
