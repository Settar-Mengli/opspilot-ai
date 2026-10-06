# D-034: GitHub MCP read-only Ask client

- **Date:** 2026-10-06
- **Status:** Accepted
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
- **Protocol era (CURRENT, pinned):** the adapter calls `ClientSession.initialize()` and requires negotiated `protocolVersion == 2025-11-25`. It does **not** use SDK “mode auto” / `_meta`-era discovery as the production path. That choice is verified by the owner C0 handshake (below), not assumed. A different negotiated version maps to `mcp_protocol_version_mismatch` (distinct from `mcp_protocol_error`).

## Handshake (C0)

`uv run python -m opspilot.integrations.github_mcp.handshake` — owner PAT in their shell. Prints protocol version, tool names, session-id **boolean**, allowlist presence. No `tools/call`. STOP if HTTP 401/402/403/404 indicates a paid Copilot entitlement (L12).

### Owner C0 result (CURRENT — 2026-10-06, owner-run; counts/names only)

| Field | Value |
|-------|--------|
| `protocol_version` | `2025-11-25` |
| `session_id_issued` | `yes` |
| `tool_count` | `4` |
| `tool_names` | `get_file_contents`, `get_me`, `list_commits`, `pull_request_read` |
| `allowlisted_present` | all four pinned names |
| `copilot_gated_advertised` | `no` |

L12 clear: no paid Copilot entitlement required for the read-only remote. Initialize-era pin in code matches this handshake.

## Secrets

Never in CI, `morning.yml`, Neon, logs, SSE, `startup_config`, PARTs, or error strings. Redaction must cover `ghp_` / `github_pat_` / Bearer.

## Status

Accepted for the off-by-default operator-gated client on branch `mcp/github-readonly`. PART 22 and LIVE counts are **owner-only** after STOP SECRETS / STOP LIVE; they are not implied by this ADR.

## Addendum (2026-10-06) — shipped client (flag off default)

- Adapter is **initialize-era only**: `ClientSession.initialize()` then one `tools/call`, session closed. Expected version constant: `EXPECTED_PROTOCOL_VERSION = "2025-11-25"`. Surprise versions → `mcp_protocol_version_mismatch`.
- `OperatorGitHubMcpAuth` is minted in Ask SSE beside Anthropic auth; types are not shared. Fail-closed gate: CI / flag / DEMO / mint / PAT / owner / repo before any SDK HTTP.
- Four static tools only. `X-MCP-Readonly`, `X-MCP-Lockdown`, `X-MCP-Tools` on adapter requests. Lockdown is a **content filter, not authorization**.
- Timeout `OPSPILOT_GITHUB_MCP_TIMEOUT_S` default 15s on the SDK/httpx2 call only (not `execute_tool`).
- Hermetic tests inject `httpx2.ASGITransport` via `set_http_client_factory`; pytest `--disable-socket` unchanged. PAT never in CI workflows.
