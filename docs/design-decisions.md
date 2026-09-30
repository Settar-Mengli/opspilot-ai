# Design decisions (portfolio index)

Short links to key ADRs. Full text lives under [docs/adr/](adr/).

| Decision | ADR | One-liner |
|----------|-----|-----------|
| Background jobs | [D-011](adr/D-011-background-jobs.md) | In-runner GHA for morning job (not Celery) |
| LLM gateway | [D-012](adr/D-012-hand-rolled-gateway.md) | Hand-rolled multi-provider gateway; no LiteLLM |
| Structured outputs | [D-013](adr/D-013-structured-outputs.md) | Schema-validated JSON with repair + failover |
| Evals | [D-018](adr/D-018-pytest-evals.md) / [D-028](adr/D-028-eval-harness.md) | Pytest + CLI harness; live leaderboard (B3) |
| Injection defenses | [D-029](adr/D-029-prompt-injection-defenses.md) | Untrusted delimiters; live ASR (not CI gate) |
| Tracing | [D-019](adr/D-019-tracing.md) | LlmCall rows + JSONL/OTel hooks |
| Anthropic prepaid | [D-023](adr/D-023-anthropic-prepaid-gate.md) | Anthropic off by default; token+USD budgets |
| Run history | [D-025](adr/D-025-run-history-postgres.md) | Postgres-only API runs; CLI files optional |
| Responsive layout | [D-026](adr/D-026-responsive-layout-policy.md) | Mobile-first + ≥1280 three-pane |

See also: [architecture.md](architecture.md) · [ROADMAP.md](../ROADMAP.md) · [OPSPILOT-MASTER-RECORD.md](../OPSPILOT-MASTER-RECORD.md)
