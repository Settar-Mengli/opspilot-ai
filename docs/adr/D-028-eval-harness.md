# D-028: Eval Harness (Pytest + CLI)

- **Date:** 2026-09-30
- **Status:** Accepted
- **Blocks:** B3
- **Related:** D-018, D-013, D-019, D-023; locks P1–P5, P9–P10

## Context

B3 needs a hermetic regression lane and an owner-gated live leaderboard without paid eval SaaS or an eval DB table.

## Decision

- Datasets: `evals/datasets/triage/v1/` (N=40, `label_version=triage-labels/v1`, append-only) and `evals/datasets/redteam/v1/` (~20 attacks).
- Code: `src/opspilot/evals/`; tests: `tests/evals/` (default pytest).
- CLI: `python -m opspilot.jobs.run_evals` — hermetic default; `--live --provider <name>` owner-gated.
- Primary CI metric: macro-F1 (unweighted mean of urgency/category/sentiment F1) for **rules vs labels**; floor **0.30** (owner-locked STOP F1-FLOOR; C6 measured ≈0.3256).
- Live: `BudgetAwareGateway`, exactly one provider per run (no failover); publish `docs/evals/leaderboard.md` + JSON artifacts (no UI, no secrets, corpus IDs only).
- Ollama: local runbook only (P9); no CI job.
- NB9 folded into first live leaderboard via per-provider validity% and repair% (P10).
- B6 promotion hook reserved in triage manifest (`promotion_hook: "b6-corrections"`).

## Acceptance criteria

- Hermetic rules-vs-labels gate in CI after owner locks floor.
- Live results committed under `docs/evals/` with Anthropic column documented as `skipped` in B3 (P7).

## Consequences

Eval numbers for portfolio (P-5) come only from in-repo artifacts. Threshold changes require explicit PR commits.
