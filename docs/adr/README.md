# Architecture Decision Records

Index of ADRs for OpsPilot. Status values: Accepted | Superseded | Proposed.

| ID | Title | Status | Blocks |
|----|-------|--------|--------|
| [D-001](D-001-python-first-local.md) | Python-first local architecture | Accepted | — |
| [D-002](D-002-rule-based-ai-simulation.md) | Rule-based AI simulation first | Accepted | — |
| [D-003](D-003-cli-first-vertical-slice.md) | CLI-first vertical slice | Accepted | — |
| [D-004](D-004-adapter-seam.md) | Adapter seam for future models | Accepted | B2 |
| [D-005](D-005-explicit-validation.md) | Explicit validation and error boundaries | Accepted | — |
| [D-006](D-006-immutable-run-history.md) | Immutable run history with latest compatibility | Accepted | B1 |
| [D-007](D-007-url-query-run-context.md) | URL query param as frontend run context | Accepted | — |
| [D-008](D-008-database.md) | Database = Neon Postgres | Accepted | B1, B4, B7 |
| [D-009](D-009-orm-migrations.md) | SQLAlchemy 2 + Alembic; Postgres in tests | Accepted | B1 |
| [D-010](D-010-async-fastapi.md) | Async FastAPI | Accepted | B1, B5 |
| [D-011](D-011-background-jobs.md) | In-process + GHA cron (no Celery) | Accepted | B6 |
| [D-012](D-012-hand-rolled-gateway.md) | Hand-rolled LLM gateway (no LiteLLM) | Accepted | B2 |
| [D-013](D-013-structured-outputs.md) | Native JSON schema/mode + Pydantic | Accepted | B2, B3 |
| [D-014](D-014-hand-rolled-agent-loop.md) | Hand-rolled bounded agent loop | Accepted | B5 |
| [D-015](D-015-embeddings.md) | No embeddings until P9-semantic trigger | Accepted | — |
| [D-016](D-016-google-oauth-testing.md) | Google OAuth Testing forever | Accepted | B4, B7 |
| [D-017](D-017-telegram-notifications.md) | Telegram notifications; web push deferred | Accepted | B6 |
| [D-018](D-018-pytest-evals.md) | Custom pytest evals CORE | Accepted | B3 |
| [D-019](D-019-tracing.md) | OTel-compatible + LlmCall/JSONL; Phoenix deferred | Accepted | B2 |
| [D-020](D-020-frontend-data-layer.md) | Fetch + hooks; TanStack later if needed | Accepted | B5 |
| [D-021](D-021-hosts.md) | FE Pages-class + BE Render-class + Neon | Accepted | B7 |
| [D-022](D-022-repo-layout.md) | Keep src/opspilot + frontend/ | Accepted | B0 |
| [D-023](D-023-anthropic-prepaid-gate.md) | Anthropic prepaid budget gate | Accepted | B2, B3, B7 |

Master record: [OPSPILOT-MASTER-RECORD.md](../../OPSPILOT-MASTER-RECORD.md).
