# D-033: HITL Approve & Send (Reply-Only)

- **Date:** 2026-10-01
- **Status:** Accepted
- **Blocks:** B5
- **Related:** D-016, D-023, D-027, D-030, D-031

## Context

Agentic Ask may draft replies, but mail must never leave the machine without explicit operator approval. Visitors under DEMO_MODE must never send. Recipients must not be taken from LLM or email-body text.

## Decision

### Flow

1. `draft_reply` tool (or equivalent) creates `mail_drafts` with **server-derived** `to_addrs`, `thread_id`, `gmail_provider_id`, `work_item_id`.
   - Recipients come from the synced work item's `sender_or_requester` (single addr-spec). **Reply-to-self is allowed** when the operator was the original sender; that yields `to_addrs` = operator address. **Allowlist is still enforced at approve/send** (unset allowlist = deny all sends).
2. Owner may **edit subject and body only** via API. Payloads containing `to_addrs`, `thread_id`, `gmail_provider_id`, `work_item_id`, or other identity/recipient fields → **4xx reject**.
3. Recompute `payload_sha256` over server-owned identity fields + current subject/body.
4. `POST /api/v1/mail/drafts/{id}/approve` (operator session required):
   - `OPSPILOT_DEMO_MODE` → **403** `demo_mode_blocks_send` (server-side, not UI-only).
   - Verify exact-payload hash.
   - Recipients re-derived from synced thread; check **`OPSPILOT_SEND_RECIPIENT_ALLOWLIST`** (comma-separated). **Unset/default = deny all sends.**
   - Idempotency key unique per **attempt**; write `mail_send_audit`. **Replay:** if the same idempotency key was already recorded, approve returns the **prior outcome** (including deny/fail flags and prior `gmail_message_id` if any) without sending again — `status: idempotent_replay`.
   - **FE (CURRENT):** mint one key per Approve attempt; reuse while in-flight (double-click). After settle (success / 403 / 409 / 429 / error), mint a **new** key so a deliberate retry after DEMO_MODE/allowlist fix can succeed. Disable Approve while pending and after Sent.
   - Atomic daily send cap (`OPSPILOT_SEND_MAX_PER_DAY`, UTC day) via transaction advisory lock + draft claim before send.
   - Gmail **reply-in-thread only** (no arbitrary compose; no calendar writes).
   - Threading headers: fetch RFC `Message-ID` via metadata; set `In-Reply-To` / `References` only when present — **never synthesize** from Gmail provider id (omit headers; rely on `threadId`).
5. **No undo window** after send.
6. Gmail send client asserts DEMO_MODE off + allowlist before token refresh / HTTP.
7. Refresh `invalid_grant` → `google_reauth_required` (401) reconnect UX; Gmail/Calendar **idempotent** HTTP retries 429/502/503 with ≤15s sleep wall. **Non-idempotent methods (POST send) are single-attempt** unless a caller explicitly opts in (nothing opts in for send).

### Addendum (post-audit fix-pass, 2026-10-02)

- Ambiguous send outcomes (timeout, connection error, 408/429/5xx after single POST, or 2xx without parseable message id) → audit `error_code=send_outcome_unknown`, draft returned to `draft`, API `502` `send_outcome_unknown`. FE copy: check Sent folder; button label `Check Sent, then re-send`.
- `send_outcome_unknown` rows **count toward** the daily send cap (same advisory-lock section as successes).
- Definitive 4xx (other than 408/429) and reauth paths leave draft `failed` (not re-approvable) — known limitation (ROADMAP **B6**).
- Send-path `invalid_grant` / 401 → `google_reauth_required` (no retry).

### Addendum (post-audit fix-pass 2, 2026-10-02) — pre-POST vs post-POST

- The send path tracks whether `messages.send` POST was issued (`GmailClient.send_post_issued`).
- Failure **before** POST (metadata GET transport/timeout/non-2xx other than 404-omit-header): `gmail_unavailable_not_sent` → audit `send_failed`, draft `draft` (re-approvable), **does not** count toward daily cap, API **503**. Metadata 401/`invalid_grant` → `google_reauth_required` as elsewhere.
- Failure **after** POST where delivery cannot be ruled out → `send_outcome_unknown` (unchanged).
- HITL last-resort: any unexpected exception after claim writes an audit row and returns coded `MailHitlError` (pre-POST → `gmail_unavailable_not_sent` / draft; post-POST → `send_outcome_unknown` / draft) — never bare 500, never leave draft stuck `approved`.
- FE: `gmail_unavailable_not_sent` → “Gmail was unavailable. Nothing was sent — try again.”; normal Approve label; `sendOutcomeUnknown` stays false.


### Non-goals

- Undo after send.
- LLM-triggered send.
- Editable recipients from FE or model output.

## Acceptance criteria

- Tests: unset allowlist deny; non-allowlisted deny; injected recipient fields on edit deny; DEMO_MODE approve 403; hash mismatch deny; agent registry has no send tool.
- Live smoke: one approved send to demo account only (allowlist).

## Consequences

Operator must set allowlist for any send. Safer demos; slightly more reconnect friction when adding `gmail.send` scope (D-016 addendum).
