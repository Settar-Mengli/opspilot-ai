# Architecture Decision Records

Index of ADRs for OpsPilot. Status values: Accepted | Superseded | Proposed.

| ID | Title | Status | Blocks |
|----|-------|--------|--------|
| [D-001](D-001-python-first-local.md) | Python-first local architecture | Accepted | — |
| [D-002](D-002-rule-based-ai-simulation.md) | Rule-based AI simulation first | Accepted | — |
| [D-003](D-003-cli-first-vertical-slice.md) | CLI-first vertical slice | Accepted | — |
| [D-004](D-004-adapter-seam.md) | Adapter seam for future models | Accepted | B2 |
| [D-005](D-005-explicit-validation.md) | Explicit validation and error boundaries | Accepted | — |
| [D-006](D-006-immutable-run-history.md) | Immutable run history with latest compatibility | Superseded (D-025) | B1 |
| [D-007](D-007-url-query-run-context.md) | URL query param as frontend run context | Accepted (deferred FE; OUT B5 → deps+U9) | deps+U9 |
| [D-008](D-008-database.md) | Database = Neon Postgres | Accepted | B1, B4, B7 |
| [D-009](D-009-orm-migrations.md) | SQLAlchemy 2 + Alembic; Postgres in tests | Accepted | B1 |
| [D-010](D-010-async-fastapi.md) | Async FastAPI | Accepted | B1, B5 |
| [D-011](D-011-background-jobs.md) | In-process + GHA in-runner cron (no Celery) | Accepted | B6, B7 |
| [D-012](D-012-hand-rolled-gateway.md) | Hand-rolled LLM gateway (no LiteLLM) | Accepted | B2 |
| [D-013](D-013-structured-outputs.md) | Native JSON schema/mode + Pydantic | Accepted | B2, B3 |
| [D-014](D-014-hand-rolled-agent-loop.md) | Hand-rolled bounded agent loop | Accepted | B5 |
| [D-015](D-015-embeddings.md) | No embeddings until P9-semantic trigger | Accepted | — |
| [D-016](D-016-google-oauth-testing.md) | Google OAuth Testing forever; encrypted refresh in Neon | Accepted | B4, B6, B7 |
| [D-017](D-017-telegram-notifications.md) | Telegram notifications; web push deferred | Accepted | B6 |
| [D-018](D-018-pytest-evals.md) | Custom pytest evals CORE | Accepted | B3 |
| [D-019](D-019-tracing.md) | OTel-compatible + LlmCall/JSONL; Phoenix deferred | Accepted | B2 |
| [D-020](D-020-frontend-data-layer.md) | Fetch + hooks; TanStack later if needed | Accepted | B5 |
| [D-021](D-021-hosts.md) | FE Pages-class + BE Render-class + Neon | Accepted | B7 |
| [D-022](D-022-repo-layout.md) | Keep src/opspilot + frontend/ | Accepted | B0 |
| [D-023](D-023-anthropic-prepaid-gate.md) | Anthropic prepaid budget gate | Accepted | B2, B3, B7 |
| [D-024](D-024-target-package-layout.md) | Target package layout (§2.1) | Accepted | B1–B7 |
| [D-025](D-025-run-history-postgres.md) | Run history SoT = Postgres (supersedes D-006) | Accepted | B1+ |
| [D-026](D-026-responsive-layout-policy.md) | Responsive layout policy (U1–U10) | Accepted | B1.5a, B1.5b, B5+ |
| [D-027](D-027-schema-conventions.md) | Schema conventions (timestamptz, IDs, money) | Accepted | B2+ |
| [D-028](D-028-eval-harness.md) | Eval harness (pytest + CLI) | Accepted | B3 |
| [D-029](D-029-prompt-injection-defenses.md) | Prompt injection defenses + red-team ASR | Accepted | B3 |
| [D-030](D-030-operator-session-cookie.md) | Operator session cookie + CORS credentials (A1) | Accepted | B4+ |
| [D-031](D-031-ask-tool-contract.md) | Ask tool contract + JSON-emulated capability map | Accepted | B5 |
| [D-032](D-032-ask-sse.md) | Ask SSE event stream | Accepted | B5 |
| [D-033](D-033-hitl-approve-send.md) | HITL approve & send (reply-only) | Accepted | B5 |
| [D-034](D-034-github-mcp-readonly-client.md) | GitHub MCP read-only Ask client | Proposed | MCP |

Master record: [OPSPILOT-MASTER-RECORD.md](../../OPSPILOT-MASTER-RECORD.md).
