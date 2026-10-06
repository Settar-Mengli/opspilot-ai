# D-034: GitHub MCP read-only Ask client

- **Date:** 2026-10-06
- **Status:** Proposed
- **Blocks:** MCP GitHub batch (`mcp/github-readonly`)
- **Related:** D-014, D-023, D-029, D-031, D-032, PART 19 / PART 21

## Context

PART 21 placed a single official GitHub MCP connection (OpsPilot as **client**, off by default, no separate database) next on the post-spine order. Ask already has a JSON-emulated allowlist (D-031) and untrusted wrapping (D-029). GitHub file and PR text must be treated as hostile. MCP is **not** an LLM provider.

## Decision

- Official Python SDK `mcp` (2.3.0 at add time). Streamable HTTP client: `mcp.client.streamable_http` on **httpx2** (already in the lock via Anthropic). The SDK package also ships **server** extras (`starlette`, `uvicorn`, `sse-starlette`, …) that OpsPilot **does not use**; accepted dependency weight.
- One remote: `https://api.githubcopilot.com/mcp/readonly` (override `OPSPILOT_GITHUB_MCP_URL` in tests only).
- Four static Ask tools: `get_me`, `get_file_contents`, `list_commits`, `pull_request_read`. Never register names from `tools/list`. Never a meta-tool.
- Three independent read-only layers plus a registry write-deny test (see batch plan L3).
- Gate: `OPSPILOT_GITHUB_MCP_ENABLED`, `OperatorGitHubMcpAuth` (not Anthropic auth), not `DEMO_MODE`, not CI. PAT `GITHUB_MCP_PAT` local env only.
- Adapter HTTP timeout default 15s (`OPSPILOT_GITHUB_MCP_TIMEOUT_S`). **Not** `execute_tool` / SQLAlchemy on a daemon thread (D-014 / `loop.py` 214–215).
- Neutralize + cap MCP payloads before the loop UNTRUSTED wrap. GitHub lockdown header is a **content filter, not an authorization boundary**.
- SDK `Client` / `ClientSession` **mode auto** at runtime (discover with initialize fallback). **U2** (which revision GitHub remote speaks) is confirmed by the owner handshake CLI, not guessed in CI.

## Handshake (C0)

`uv run python -m opspilot.integrations.github_mcp.handshake` — owner PAT in their shell. Prints protocol version, tool names, session-id **boolean**, allowlist presence. No `tools/call`. STOP if HTTP 401/402/403/404 indicates a paid Copilot entitlement (L12).

## Secrets

Never in CI, `morning.yml`, Neon, logs, SSE, `startup_config`, PARTs, or error strings. Redaction must cover `ghp_` / `github_pat_` / Bearer.

## Status

Proposed until adapter + LIVE; then Accepted addendum.
