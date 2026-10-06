# Trust and data handling

CURRENT behavior for OpsPilot’s local operator demo. This is not a privacy policy for a public product — there is no public deploy (B7 backlog).

Re-verify provider terms at the source before treating any training/retention sentence as compliance advice.

## What leaves the app

| Path | Destination | Fields (names) | Caps / controls | Source |
|------|-------------|----------------|-----------------|--------|
| Triage LLM | Winning provider in gateway order | `source`, `subject`, `body`, `sender`, `tags` | 32 / 160 / **500** / 80 / 120; untrusted wrap | `src/opspilot/adapters/gateway_triage.py` (`build_triage_user_prompt`) |
| Ask compact context | Same | `id`, `urgency`, `category`, `urgency_reason` (± title) | ≤20 items; reason ≤120 | `src/opspilot/services/_llm.py` (`compact_triage_lines`) |
| Ask `get_message` tool | Returned into later model turns | `subject`, `body`, `sender`, ids | subject 200; body **500**; sender 120 | `src/opspilot/agent/tools/get_message.py` |
| Gmail sync | Google APIs (operator OAuth) | headers + text body | Attachments ignored (`filename` parts skipped) | `src/opspilot/integrations/gmail_client.py` |
| HITL send | Gmail send (operator) | approved subject/body/to | Allowlist; daily cap; `DEMO_MODE` blocks | `src/opspilot/services/mail_hitl.py`, D-033 |
| Telegram | Telegram Bot API | Morning outcome **counts only** | Skipped if token/chat unset | `src/opspilot/integrations/telegram_client.py` |
| GitHub MCP | GitHub MCP HTTP | Read-tool results (neutralized) | Flag off default; operator-only; CI blocked | `src/opspilot/integrations/github_mcp/gate.py`, D-034 |

## Inference tiers

| Tier | Privacy note | Wiring |
|------|--------------|--------|
| Local Ollama | Stays on the machine if `OLLAMA_BASE_URL` is local | Constructible; add `ollama` to `INFERENCE_PROVIDER_ORDER` and set budgets (not in default order) |
| Rules-only | No remote LLM HTTP when `OPSPILOT_FORCE_RULES` or `OPSPILOT_LLM_DISABLE` | `src/opspilot/llm/policy.py` (`llm_allowed`) — does not stop Google/Telegram/DB |
| Free-tier hosted | Default path: Gemini → Groq → Mistral → Cloudflare → OpenRouter | `.env.example` `INFERENCE_PROVIDER_ORDER`. **Verified 2026-10-06** against [Gemini API Additional Terms](https://ai.google.dev/gemini-api/terms): unpaid Gemini API quota is an Unpaid Service — Google may use submitted content and generated responses to provide, improve, and develop Google products and ML technologies, and human reviewers may process API input/output; Paid Services (API via a Cloud Project with an active billing account) state that prompts/responses are not used to improve products. Other providers: verify at their docs before claiming retention behavior. |
| Anthropic prepaid | Operator Ask/Sync only; token + USD ledger; off by default | D-023; never visitor Ask |

## Minimization already in place

- Triage/Ask body caps (500 chars on triage prompt and `get_message`).
- Untrusted delimiters + neutralization (D-029).
- No attachment bodies from Gmail.
- Compact Ask context (ids/labels/short reasons), not full mail dumps by default.
- HITL approve before any send; recipient allowlist.

## Not solved

- Google disconnect deletes credential + cursors and clears the operator cookie; **synced `work_items` / meetings remain** (`disconnect_google` in `src/opspilot/api/v1/oauth_routes.py`).
- Provider retention windows and training policies for Groq, Mistral, Cloudflare, and OpenRouter are not asserted here.
- Local API is bind-to-localhost by design; it is not authenticated for public internet use.

## Related

- [README.md](../README.md)
- [docs/runbooks/zero-spend.md](runbooks/zero-spend.md)
- [docs/adr/D-023-anthropic-prepaid-gate.md](adr/D-023-anthropic-prepaid-gate.md)
- [docs/adr/D-029-prompt-injection-defenses.md](adr/D-029-prompt-injection-defenses.md)
- [docs/adr/D-033-hitl-approve-send.md](adr/D-033-hitl-approve-send.md)
