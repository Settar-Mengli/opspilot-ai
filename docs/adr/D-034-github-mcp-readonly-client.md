# D-034: GitHub MCP read-only Ask client

- **Date:** 2026-10-06
- **Status:** Accepted (CURRENT for shipped + LIVE-proven clauses below; TARGET only where labeled)
- **Blocks:** MCP GitHub batch (`mcp/github-readonly`) — LIVE PASS 2026-10-06 (PART 22)
- **Related:** D-014, D-023, D-029, D-031, D-032, PART 19 / PART 21 / PART 22

## Context

PART 21 placed a single official GitHub MCP connection (OpsPilot as **client**, off by default, no separate database) next on the post-spine order. Ask already has a JSON-emulated allowlist (D-031) and untrusted wrapping (D-029). GitHub file and PR text must be treated as hostile. MCP is **not** an LLM provider.

## Decision (CURRENT — shipped)

- Official Python SDK `mcp` (2.3.0 at add time). Streamable HTTP client: `mcp.client.streamable_http` on **httpx2**. The SDK package also ships **server** extras (`starlette`, `uvicorn`, `sse-starlette`, …) that OpsPilot **does not use**; accepted dependency weight.
- One remote: `https://api.githubcopilot.com/mcp/readonly` (override `OPSPILOT_GITHUB_MCP_URL` in tests only).
- Four static Ask tools: `get_me`, `get_file_contents`, `list_commits`, `pull_request_read`. Never register names from `tools/list`. Never a meta-tool.
- Three independent read-only layers plus a registry write-deny **mutation** test (L3).
- Gate: `OPSPILOT_GITHUB_MCP_ENABLED` (default off), `OperatorGitHubMcpAuth` (not Anthropic auth), not `DEMO_MODE`, not CI (`GITHUB_ACTIONS`). PAT `GITHUB_MCP_PAT` local env only. Owner/repo env pin overwrites model args.
- Adapter wall timeout default 15s (`OPSPILOT_GITHUB_MCP_TIMEOUT_S`) → `mcp_timeout`. **Not** `execute_tool` / SQLAlchemy on a daemon thread (D-014).
- Neutralize + cap MCP payloads before the loop UNTRUSTED wrap (login ≤64; file ≤2000; commit message ≤200; PR body ≤500). GitHub lockdown header is a **content filter, not an authorization boundary**.
- **Protocol era (CURRENT, pinned):** `ClientSession.initialize()` and require negotiated `protocolVersion == 2025-11-25`. Production path does **not** use SDK mode auto / `_meta`-era discovery. Mismatch → `mcp_protocol_version_mismatch`. HTTP status → `mcp_http_4xx` / `mcp_http_5xx` (distinct from `mcp_protocol_error`).
- MCP absent from providers, budgets, and `llm_calls` as provider `mcp`.

## Handshake (C0) — CURRENT

Owner-run 2026-10-06 (counts/names only): `protocol_version=2025-11-25`, `session_id_issued=yes`, `tool_count=4`, four pinned names present, `copilot_gated_advertised=no`. Initialize-era pin matches remote. **L12 clear** (no paid Copilot entitlement for read-only).

## STOP LIVE — CURRENT (owner-run 2026-10-06 on Neon; counts/names only)

Flag-off control: no MCP tool call. Flag on: `GITHUB_MCP_ENABLED=1`. All four tools called with `ok=true`. Visitor/no cookie: core tools only; zero MCP calls. No repo writes in the LIVE window. `mcp_timeout=0`; no `mcp` in `llm_calls` providers. Details: PART 22.

## Secrets

Never in CI, `morning.yml`, Neon, logs, SSE, `startup_config`, PARTs, or error strings. Redaction covers `ghp_` / `github_pat_` / Bearer (**CURRENT**). Other GitHub token prefixes (`gho_`, `ghu_`, …) are **TARGET** unless LIVE uses them.

## TARGET / deferred (not CURRENT)

- Outer `asyncio.timeout` still wraps initialize **plus** `tools/call` (not HTTP-only). Documented; not a LIVE blocker.
- Morning Run scheduled E2E remains unproven (PART 20 / 21).
- Gemini key rotation after local-log exposure during LIVE is an **owner ops** action (no value in git).

## Status

Accepted. Shipped on `mcp/github-readonly` tip `7755c3c`; LIVE PASS recorded in PART 22. Flag off by default; operator-only.
