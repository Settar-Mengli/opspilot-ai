# Ask + HITL send (B5)

Operator path for agentic Ask (SSE) and approve-to-send Gmail replies.

## Env

| Variable | Meaning |
|----------|---------|
| `OPSPILOT_ASK_MAX_STEPS` | Agent tool-loop steps (default **5**) |
| `OPSPILOT_ASK_MAX_PROVIDER_CALLS` | Provider calls per Ask (default **8**) |
| `OPSPILOT_ASK_STEP_TIMEOUT_S` | Per-step wall timeout after provider return (default **30**) |
| `OPSPILOT_SEND_RECIPIENT_ALLOWLIST` | Comma-separated emails (case-insensitive; display-name forms OK); **unset/empty = deny all sends** |
| `OPSPILOT_SEND_MAX_PER_DAY` | Successful sends per UTC day (default **5**); exceed → **429** |
| `OPSPILOT_DEMO_MODE` | `1` → approve/send returns **403** |
| `OPSPILOT_CORS_ORIGINS` | Allowed Origin/Referer for cookie mutating routes (CSRF) |
| `OPSPILOT_COOKIE_SECURE` | `1` in production → Secure cookie flag (SameSite=Lax always) |

Never print allowlist contents or tokens in logs/chat.

## OAuth reconnect for `gmail.send`

Scopes now require `gmail.readonly` + **`gmail.send`** + `calendar.readonly` (D-016). After pulling B5:

1. Disconnect Google in Connections (or clear credential).
2. Connect again so Google shows consent including send.
3. Confirm Capabilities / credential scopes include send.

## Ask stream

- UI uses `POST /api/v1/ask/stream` (`text/event-stream`).
- Compat: `POST /api/v1/ask` still returns final text only.
- Events: `token`, `tool_start`, `tool_end`, `draft`, `final`, `error` (+ `request_id`).
- Anthropic is never on the Ask path.

## Draft → approve → send

1. Agent may call `draft_reply` (writes `mail_drafts` only — **no send tool**).
2. Operator edits **subject/body only** via `POST /api/v1/mail/drafts/{id}/edit` (forbidden: `to_addrs`, thread/provider/work_item ids).
3. `POST /api/v1/mail/drafts/{id}/approve` with `payload_sha256` + operator cookie.
4. Server sends **reply-in-thread** only; recipients from synced thread; allowlist + DEMO_MODE gates; `mail_send_audit` row.

## Smoke counts (no bodies/secrets)

Record: tool events, llm_calls, steps, audit +1, DEMO_MODE 403, allowlist deny, deleted-sync row delta.
