# AGENTS

Operating rules for AI-assisted and human development in this repository.

## Grounding

> Ground every decision in what the repo actually is. Record facts as CURRENT only when verified in code; label everything planned as TARGET. Recommend, record, and build like a production engineer — no padding, no aspirational claims presented as fact.

Canonical plan: [OPSPILOT-MASTER-RECORD.md](OPSPILOT-MASTER-RECORD.md) · [ROADMAP.md](ROADMAP.md) (B0–B7) · [docs/architecture.md](docs/architecture.md) · [docs/adr/](docs/adr/)

## Zero-spend

1. No further paid API purchase.
2. Default LLM path = free tiers + Ollama + rules — **never** Anthropic by default.
3. Anthropic only via existing prepaid credits, allowlisted tasks, and gateway **token + USD** budget (D-023). Never in tests/CI. Never for visitor Ask.
4. Fictional demo data only; Google OAuth stays Testing; visitors never connect Gmail.
5. Do not invent quota numbers — VERIFY AT DECISION TIME.

## Hermetic tests

- Default pytest suite must not call live LLMs.
- Prefer fakes/tmp dirs; no reliance on repo `data/output` order.
- If a key is present in `.env`, tests must still not spend.

## Core workflow

1. Explain before edit.
2. Keep changes small and reviewable; one batch branch at a time (`bN/...`).
3. Do not implement outside approved scope or pull CUT-list items without an explicit trigger decision.
4. After each coding step, produce an implementation report:
   - What changed · Files created/edited · How to run · How to test · Recommendations

## Testing

- Behavior changes need tests or a written deferral reason.
- Prefer deterministic tests over flaky heuristics.
- Validate relevant tests before closing a step.

## Safe git

- No destructive commands (`git reset --hard`, force-push to main) unless explicitly requested.
- Never revert unrelated user changes.
- Commits focused on one intent.

## Documentation

- Update the master record / ROADMAP / ADRs when decisions change — **not** a separate PROGRESS.md (retired in B0).
- Minimize secrets in docs (X4); never paste `.env` values into chat or commits.

## Scope constraints (early batches)

- Local-only until the batch that introduces the integration
- No paid API dependency
- No real external service integrations before their locked batch (B4+)
