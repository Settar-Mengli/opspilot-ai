# D-031: Ask Tool Contract + Capability Map (JSON-Emulated v1)

- **Date:** 2026-10-01
- **Status:** Accepted
- **Blocks:** B5
- **Related:** D-014, D-012, D-029, D-033

## Context

B5 Agentic Ask needs a bounded, allowlisted tool surface without LangGraph/MCP and without per-provider native tool APIs that would break uniform failover mid-loop.

## Decision

### Allowlist (v1)

| Tool | Kind | Effect |
|------|------|--------|
| `search_items` | read | Search/filter work items (G7 source filter preserved) |
| `get_message` | read | Fetch one work item / message fields |
| `get_calendar` | read | Fetch meetings in a window |
| `draft_reply` | write-prep | Create/update `mail_drafts` only; **no** Gmail HTTP send |

**Send is not a tool.** The LLM cannot invoke send. Approve & send is HITL only (D-033).

### Arg schemas (prompt contract)

Emitted in `TOOL_SYSTEM_FRAGMENT` (code is authoritative):

| Tool | Args |
|------|------|
| `search_items` | `query:string`, `limit?:int<=20` |
| `get_message` | `id:string` (work item PK) |
| `get_calendar` | `days?:int<=14` |
| `draft_reply` | `work_item_id\|id:string`, `body:string`, `subject?:string` (model `subject` **ignored**) |

**Rule:** `draft_reply.work_item_id` must be the exact `id` from `search_items` / `get_message` or the triage context — **never** a Gmail provider/thread id. Work item ids in prompts are never truncated below PK length (String(64); `wi_{uuid4.hex}` is 35 chars).

**Subject (CURRENT):** model-supplied `subject` is **ignored**. Server always sets `Re: <original>` without stacking `Re:`. Owner may change subject only via HITL edit (D-033). Body is required.

**Arg shape normalization (CURRENT):** accept `args` / `arguments` / `parameters` / `input` bags or flat top-level tool fields; conflicting non-identical bags → reject.

**Sticky final provider (CURRENT):** after a successful tool step, subsequent `complete_json` turns pass `prefer_provider` = last tool provider (then remaining order; still honors `exclude_providers` / circuit failover).

**Schema enforcement (CURRENT):** validate required args **before** `execute_tool`. On violation, do not execute; send one content-free repair turn (counts toward provider-call cap). Still invalid → **one** failover retry on the next provider in Ask routing order (also counts toward the provider-call cap; logged as `ask_provider_failover` with codes only). If that also fails or no next provider → soft final `tool_args_invalid`.

Few-shot examples in the system fragment use placeholder ids only (no live mail content).

### Transport

- **JSON-emulated tool calls for ALL providers** in B5 (uniform across failover).
- Native provider tools = **future ADR**, not B5.
- Arguments validated against per-tool JSON Schema before execution; invalid args → tool error event, no side effects.

### Capability map (CURRENT for B5)

Every free-tier provider used on Ask (`gemini`, `groq`, `mistral`, `cloudflare`, `openrouter`, `ollama`, `fake`) = **JSON-emulated**. Unsupported = omit from Ask route (Anthropic never on `ask`).

### Caps (see D-014 addendum)

- `OPSPILOT_ASK_MAX_STEPS` default **5**
- `OPSPILOT_ASK_MAX_PROVIDER_CALLS` default **8** per Ask

### Scope note (B5)

**IN:** M6+M7 tools/SSE/HITL, Gmail deleted-message removal, DM-09 `ttft_ms` on Ask, dual-loop touch only on agent path.  
**OUT (reassign at closeout to deps+U9/OD):** D-007, FE code-splitting, `generated.ts`, duplicate `getTriage`, CQ-04, F-11.

## Acceptance criteria

- Hermetic FakeProvider scripted tool traces; allowlist grep proves no `send_*` tool.
- Invalid tool args rejected without DB/Gmail side effects.
- Live smoke: JSON-emulated tools succeed on at least one free-tier provider under caps.

## Consequences

Simpler failover story; slightly higher prompt tokens vs native tools. Native tools can be added later without changing HITL/send invariants.

## Addendum (MCP GitHub, 2026-10-06) — dynamic allowlist

Ask JSON-emulated transport is unchanged. When `OPSPILOT_GITHUB_MCP_ENABLED` is on, DEMO is off, CI is off, and `OperatorGitHubMcpAuth` is minted, `allowed_tools()` adds four **read** names: `get_me`, `get_file_contents`, `list_commits`, `pull_request_read`. Flag off → original four only; MCP names fail `tool_not_allowlisted` before `execute_tool`. Owner/repo are **env-pinned**, never model-chosen. MCP is not a provider and is not in `INFERENCE_PROVIDER_ORDER`. Write GitHub MCP names stay off the registry (`assert_no_write_mcp_tools`).
