# D-032: Ask SSE Event Stream

- **Date:** 2026-10-01
- **Status:** Accepted
- **Blocks:** B5
- **Related:** D-010, D-014, D-020, D-030

## Context

Ask UX needs progressive feedback (tokens, tool steps, drafts) without WebSockets. Operator session uses cookies (D-030); EventSource cannot send cookies cross-origin reliably with our local FE/API split.

## Decision

- Route: **`POST /api/v1/ask/stream`** → `text/event-stream`.
- FE: **`fetch` + ReadableStream** with `credentials: 'include'`. **No EventSource.**
- Events (each includes `request_id`):

| Event | Purpose |
|-------|---------|
| `token` | Text delta (buffered-complete chunks acceptable for v1) |
| `tool_start` | Tool name + args summary (no secrets) |
| `tool_end` | Tool name + status + minimized result |
| `draft` | Draft id + subject/body preview for HITL card |
| `final` | Terminal answer / completion |
| `error` | Soft or hard failure; stream ends |

- Client disconnect / AbortController = **abort** in-flight loop; **no** auto-resume or replay of tools/sends.
- Provider `stream()` may remain complete-then-one-chunk; SSE is the **agent event** stream, not necessarily true HTTP token streaming from the model vendor.
- Keep non-stream `POST /api/v1/ask` as compat returning final text only.

## Acceptance criteria

- Hermetic API test consumes SSE events in order for a FakeProvider scripted Ask.
- FE AbortController cancels without orphan Gmail writes (send only via HITL).
- `ttft_ms` recorded on first `token` when persisting `LlmCall` (DM-09).

## Consequences

Buffered TTFT may be close to full latency until true vendor streaming is added; UX still gains tool timeline and draft events.
