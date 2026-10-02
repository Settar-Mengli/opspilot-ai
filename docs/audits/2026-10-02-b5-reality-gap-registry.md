# B5 reality-gap registry (F1–F17) — 2026-10-02

Source: plan file `b5_reality-gap_fix_c8b43d3c.plan.md` plus post-audit ledger / amended fix-pass plan.
Unsourced items = **NOT-DEFINED** (never invented).

| Id | Definition | Status after post-audit fix-pass | Commits / tests |
|----|------------|----------------------------------|-----------------|
| F1 | Server-owned `Re:` subject; ignore model subject | DONE (prior reality-gap pass) | draft_reply + D-031 tests |
| F2 | Per-attempt idempotency key + in-flight lock | DONE (prior) | App/AskDock + hermetic |
| F3 | Sync status this-sync vs totals copy | DONE; Vitest added in C7 | `bb1caa2`; ConnectionsPage tests |
| F4 | Demo inbox third-party mail cleanup | Owner pre-B7; **not** a merge gate | — |
| F5 | Host-label-only discipline | DONE (hardening); PART Neon cell redacted C8 | PART 13 hostname note |
| F6 | Gmail pagination + cursor safety | DONE; C3 adds truncate-without-hid → full list + `gmail_truncated` | history tests |
| F7 | Calendar pagination + syncToken safety | DONE; C2 clears token + absence reconcile | calendar tests |
| F8 | SPAM label removal | DONE (prior) | gmail_client history |
| F9 | RFC Message-ID or omit | DONE; metadata failure before send → `gmail_unavailable_not_sent` (fix-pass 2) | send_reply metadata |
| F10 | invalid_grant + capped backoff | DONE; C1 send single-attempt + outcome classify; fix-pass 2 pre/post POST split | mail/http tests |
| F11 | Sticky final provider | DONE (prior) | loop prefer_provider |
| F12 | Fixed Ask final after draft | DONE (`90177ff` era) | — |
| F13 | Alias of F2 | DONE | — |
| F14 | Live smoke script + sanitized fixtures | Script shipped `e57c701` but **called non-existent** `/api/v1/oauth/google/sync` and `/api/v1/oauth/google/status` — **could not have passed as written**. C6 rewrote guards/`--send`/correct sync path. Fixtures wired C4; token_error + llm_turns behavioural in fix-pass 2. **Live smoke NOT run.** | C4, C6, D3 |
| F15 | Owner gallery approval | **approved** — owner quote `gallery approved` — 2026-10-02; before run **37053916564**, compare run **37054725997** | STOP VISUAL closed (PART 13) |
| F16 | Docs (ROADMAP/CHANGELOG/PART/ADRs) | Updated post-audit + fix-pass 2 | PART 13 subsections |
| F17 | startup_config expansion | DONE (prior `29ac4f7`) | — |

## Known limitation (A3)

Definitive mail send failures leave draft status `failed` (not re-approvable). Ambiguous `send_outcome_unknown` returns draft to `draft` for deliberate re-send. Pre-POST `gmail_unavailable_not_sent` also returns to `draft` (not capped). Reopen-failed path deferred — see ROADMAP Open findings (**B6**).
