# Ask + HITL send (B5)

Operator path for agentic Ask (SSE) and approve-to-send Gmail replies.

## Env

| Variable | Meaning |
|----------|---------|
| `OPSPILOT_ASK_MAX_STEPS` | Agent tool-loop steps (default **5**) |
| `OPSPILOT_ASK_MAX_PROVIDER_CALLS` | Provider calls per Ask (default **8**) |
| `OPSPILOT_ASK_STEP_TIMEOUT_S` | Per-step **wall-clock** timeout around the provider call (default **30**) |
| `OPSPILOT_SEND_RECIPIENT_ALLOWLIST` | Comma-separated emails (case-insensitive; display-name forms OK); **unset/empty = deny all sends** |
| `OPSPILOT_SEND_MAX_PER_DAY` | Successful sends per UTC day (default **5**); exceed → **429** |
| `OPSPILOT_DEMO_MODE` | `1` → approve/send returns **403** |
| `OPSPILOT_CORS_ORIGINS` | Shared allowlist for **CORSMiddleware** and CSRF Origin/Referer (default **`http://127.0.0.1:5173`**) |
| `OPSPILOT_CSRF_RELAX_DEV` | Dev/TestClient only. **Must stay unset for live** — browser sends Origin |
| `OPSPILOT_COOKIE_SECURE` | `1` in production → Secure cookie flag (SameSite=Lax always). Keep unset on local HTTP |

Never print allowlist contents or tokens in logs/chat.

**Live UI origin:** use **`http://127.0.0.1:5173`** (not `localhost`) so cookie + CSRF + CORS agree.

## Idempotent approve replay (D-033)

If `idempotency_key` was already written to `mail_send_audit`, approve returns the **prior outcome** (`status: idempotent_replay`) — including allowlist deny / send fail flags and prior `gmail_message_id` when present — **without sending again**.

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
- Client disconnect aborts before the next provider call (no further drafts).

## Draft → approve → send

1. Agent may call `draft_reply` (writes `mail_drafts` only — **no send tool**).
2. Operator edits **subject/body only** via `POST /api/v1/mail/drafts/{id}/edit` (forbidden: `to_addrs`, thread/provider/work_item ids).
3. `POST /api/v1/mail/drafts/{id}/approve` with `payload_sha256` + operator cookie.
4. Server sends **reply-in-thread** only; recipients from synced thread; allowlist + DEMO_MODE gates; `mail_send_audit` row.
5. Daily send cap + draft claim are serialized with a UTC-day advisory lock.

### Approve / send error codes (CURRENT)

| Failure class | Audit `error_code` | API code / HTTP | Draft status | Re-approvable | Counts toward daily cap |
|---------------|--------------------|-----------------|--------------|---------------|-------------------------|
| Pre-POST Gmail unavailable (metadata timeout/5xx/…) | `gmail_unavailable_not_sent` | same / **503** | `draft` | Yes | **No** |
| Ambiguous after POST (timeout/408/429/5xx/opaque 2xx) | `send_outcome_unknown` | same / **502** | `draft` | Yes (new key; check Sent) | **Yes** |
| Reauth (`invalid_grant` / 401) | `google_reauth_required` | same / **401** | `failed` | No | No |
| Definitive send 4xx (other) | original / mapped | `gmail_send_failed` / 400 | `failed` | No | No |
| Daily cap | `send_daily_cap` | same / **429** | unchanged | — | No (deny row) |

FE: unknown → “Check Sent, then re-send”; unavailable → “Gmail was unavailable. Nothing was sent — try again.” (normal Approve label).

## Corrected STOP LIVE (ordered, counts only)

**Preconditions**

- FE: **http://127.0.0.1:5173** only (not `localhost`).
- API: **http://127.0.0.1:8000**.
- Do **not** set `OPSPILOT_CSRF_RELAX_DEV`.
- Do **not** set `OPSPILOT_COOKIE_SECURE=1` on local HTTP.
- Apply Alembic **0009** on Neon before approve/send.

**0. Host label only (no secrets)**

```bash
# Print host label only — never print full DATABASE_URL / passwords
uv run python -c "import os,re; from opspilot.config.env_load import load_repo_dotenv; load_repo_dotenv(); u=os.environ.get('DATABASE_URL',''); m=re.search(r'@([^/:]+)', u or ''); print('host=', m.group(1) if m else '(unset)')"
```

**1. Pre-counts (read-only SQL)**

```sql
SELECT version_num FROM alembic_version;
SELECT COUNT(*) AS work_items FROM work_items;
SELECT COUNT(*) AS llm_calls FROM llm_calls;
SELECT COUNT(*) AS mail_drafts FROM mail_drafts;
SELECT COUNT(*) AS mail_send_audit FROM mail_send_audit;
```

Record before. Re-measure; do not assume prior snapshots.

**2. Apply 0009 (owner go)**

```bash
uv run alembic current
uv run alembic upgrade head   # expect 0009_mail_send_audit_failed
uv run alembic current
```

Re-run counts. Expand-only: new columns with defaults; verify no unexpected drops in pre-existing table counts.

**3. Process env (local `.env`, never paste secrets)**

- `OPSPILOT_DEMO_MODE=0` for real send; `=1` for 403 gate check.
- `OPSPILOT_SEND_RECIPIENT_ALLOWLIST=<one demo addr>`
- Caps optional: `OPSPILOT_ASK_*`, `OPSPILOT_SEND_MAX_PER_DAY` (default 5).
- Google OAuth client must show **`gmail.send`** on consent (Cloud Console + Testing users).
- **Must unset** `OPSPILOT_FORCE_RULES` and `OPSPILOT_LLM_DISABLE` for live Ask (agent shells often inherit `FORCE_RULES=1` from pytest).
- After API start, **require** the `startup_config …` log line: confirm `FORCE_RULES=0`, `DEMO_MODE` as intended, `allowlist_count` (≥1 for send), `ANTHROPIC_ENABLED=0`. Also confirm `opspilot.api.access` lines include `request_id=` on each request.

**4. OAuth reconnect**

1. Connections → Disconnect → Connect (CORS allows DELETE from `127.0.0.1:5173`).
2. Confirm stored scopes include `gmail.send` (Capabilities / DB scopes string — no tokens in chat).

**5. Smoke (counts only — no bodies/subjects/tokens in records)**

1. Ask/stream happy path → token/final; note step/provider counts.
2. Tool path → draft event; `mail_drafts` +1.
3. Edit subject/body → 200; hash changes.
4. Approve once → `mail_send_audit` +1 with `gmail_message_id`; draft `sent`.
5. Approve again → **409**.
6. `DEMO_MODE=1` approve → **403** + audit flag.
7. Unset allowlist → **403**.
8. Optional: hit daily cap → **429**.
9. Idempotent key replay → prior outcome (`idempotent_replay`), no second send.

**6. Gallery**

Owner approves ask-error `-linux.png` baselines (375 required) when reviewing the PR. Do not claim approval in PART without owner sign-off.

**7. Rollback**

`alembic downgrade 0008_ask_hitl_send` drops the 0009 columns only (owner decision).

## Automated live smoke script (owner-run only)

`scripts/live_smoke_b5.py` — **do not run in CI** and was **not executed** in the B5 post-audit fix-pass Build.

```bash
# Preconditions: allowlist exactly one address == connected operator Google email;
# gmail.send on stored scopes; Alembic head matches repo; Anthropic off; FORCE_RULES/LLM_DISABLE unset;
# existing operator credential in DB; free LLM path available for Ask draft.
# Default = NO real send. Real send requires --send (still capped at one).
uv run python scripts/live_smoke_b5.py          # default: preflight + sync + Ask + demo/allowlist 403
uv run python scripts/live_smoke_b5.py --send   # + one real approve send + 409 + idempotent replay
```

Behavior (process-only env; never writes `.env`; DB access = read-only counts + API writes only):

1. Print `mode=` and `database_host=` (first label only).
2. Hard preflight (non-zero exit, codes only): Anthropic enabled; FORCE_RULES/LLM_DISABLE set; allowlist ≠ exactly operator; Alembic head mismatch (revision ids); `gmail_send_scope=N`.
3. Mint operator cookie via `issue_session` (never prints cookie/token values).
4. Start/stop uvicorn per phase on `127.0.0.1:8010`.
5. Sync via `POST /api/v1/sync` (status code only); Ask draft (LLM asks capped at 3 per run; prints `llm_asks_used`).
6. Default mode: print `expect_409=skipped`; no real send. `--send`: one approve send (unknown outcome counts as the one send and stops further sends) → 409 re-approve → idempotent replay.
7. Phase demo (`DEMO_MODE=1`): approve → 403.
8. Phase allowlist empty: approve → 403.
9. Teardown child processes; print COUNT deltas only.

At most **one** real Gmail send for the entire `--send` run; default mode must print `real_sends_total=0`.
