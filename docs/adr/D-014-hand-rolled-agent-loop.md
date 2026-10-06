# D-014: Hand-Rolled Bounded Agent Loop

- **Date:** 2026-09-26
- **Status:** Accepted
- **Blocks:** B5

## Context

Agentic Ask needs tools + multi-turn without cloning LangGraph HITL from the other portfolio repo.

## Decision

Hand-rolled loop with hard step cap (e.g. 4–6), read-only tools until approve&send, SSE for tokens/tool events. No LangGraph/CrewAI.

## Alternatives considered

LangGraph; crew frameworks; single-shot Ask only.

## Options

| Option | Tradeoffs |
|--------|-----------|
| (a) Hand-rolled bounded loop | Complementary portfolio; full control |
| (b) LangGraph | Overlap with other repo |
| (c) Single-shot Ask only | No tools |

## Acceptance criteria

- B5: step/time/token caps enforced; send requires approval; SSE events \	oken|tool_start|tool_end|final|error\.

## Consequences

Complementary portfolio story; quota burn risk — gate with metering and evals (B3 before/with tools on real bodies).

## Addendum (B5, 2026-10-01) — caps

Locked env defaults (fail closed when exceeded):

| Var | Default | Meaning |
|-----|---------|---------|
| `OPSPILOT_ASK_MAX_STEPS` | **5** | Max tool/LLM loop iterations per Ask |
| `OPSPILOT_ASK_MAX_PROVIDER_CALLS` | **8** | Max provider HTTP attempts per Ask (steps + repair + failover) |

Server-side multi-turn history: last **10** turns, each turn length-capped; tool outputs in history treated as UNTRUSTED (D-029). Daily UTC provider budgets unchanged (B2). Anthropic never on `ask` (D-023). SSE event set extended with `draft` (D-032).

## Addendum (MCP GitHub, 2026-10-06) — adapter timeout not execute_tool

`OPSPILOT_ASK_STEP_TIMEOUT_S` still wraps **provider** `complete` / `complete_json` only. GitHub MCP HTTP is bounded by `OPSPILOT_GITHUB_MCP_TIMEOUT_S` (default **15**) inside `integrations.github_mcp.client` (`asyncio.timeout` around the SDK Streamable HTTP call). Do **not** wrap `execute_tool` in a daemon thread / SQLAlchemy-unsafe timeout (D-034). Disconnect poller still cannot abort an in-flight MCP call; 15s is the wall bound. `mcp_timeout` maps to a content-free tool error + existing repeat-failure soft final.
