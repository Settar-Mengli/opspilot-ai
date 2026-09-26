# OpsPilot Architecture

**Dualism:** Sections labeled **CURRENT** describe post-B1 behavior on `main` (B0 and B1 merged). Sections labeled **TARGET** describe the remaining locked rebuild (B2–B7). Do not present TARGET as shipped.

Master record: [OPSPILOT-MASTER-RECORD.md](../OPSPILOT-MASTER-RECORD.md) · ADRs: [docs/adr/](adr/) · Roadmap: [ROADMAP.md](../ROADMAP.md)

---

## Design principles

1. Ground CURRENT vs TARGET honestly.
2. Adapter / gateway first — providers are commodities.
3. Zero further spend; free tiers + Ollama; Anthropic prepaid-gated only (D-023).
4. Hermetic tests — no live LLM in default suite/CI.
5. Calm UX — chief-of-staff voice, not alert spam.
6. Complementary portfolio — hand-rolled gateway/agent; no LangGraph/Celery clone.

---

## CURRENT (B1 — hermetic foundation)

Verified on `main` (B1 merge `c5de149`): hermetic pytest (socket block + `OPSPILOT_FORCE_RULES`), Postgres via Compose/CI, **sync** SQLAlchemy 2 + `psycopg`, `/api/v1` with envelope, in-process API pipeline (Postgres-only persist), Settings GET-only (`provider`/`model`/`api_key_set` — no key preview), FE on `/api/v1`, coverage fail-under **72**, Node 24 / Python 3.13 / uv.

### Endpoints (CURRENT) — `/api/v1`

Primary surface is **`/api/v1/*`**. Legacy unversioned routes were removed in B1 commit 9.

| Method | Path |
|--------|------|
| GET | `/api/v1/health` |
| GET | `/api/v1/settings` (read-only; no key material) |
| POST | `/api/v1/runs` (in-process pipeline + Postgres persist) |
| GET | `/api/v1/runs`, `/api/v1/runs/{run_id}` |
| GET | `/api/v1/triage` (includes AI-05 lite `subject_or_title`) |
| GET | `/api/v1/briefing`, `/api/v1/ai-briefing` |
| GET | `/api/v1/runs/{run_id}/triage`, `.../briefing`, `.../ai-briefing` |
| POST | `/api/v1/ask`, `/api/v1/evening-summary`, `/api/v1/insights` |
| GET | `/api/v1/inputs`, `/api/v1/capabilities` |

Notable: **no** `PATCH` settings. Pipeline runs **in-process** (no CLI subprocess).

### Modules (path map)

| Path | Role |
|------|------|
| `src/opspilot/api/app.py` | FastAPI app + `/api/v1` |
| `src/opspilot/api/v1/` | Versioned routes |
| `src/opspilot/persistence/` | SQLAlchemy models + engine |
| `src/opspilot/jobs/import_json.py` | X5 importer |
| `src/opspilot/pipeline/` | Daily ops orchestration (`run_daily_ops.py`) |
| `src/opspilot/adapters/` | rule_based, claude, conversation, evening, insights, briefing, factory, base |
| `frontend/src/api/` | `/api/v1` client only |
| `data/raw/` | Sample JSON inputs (API/CLI read) |
| `data/output/`, `data/history/` | CLI `--output` export only (not API SoT) |

### Data flow (CURRENT)

```
API: sample_input.json → in-process pipeline → Postgres only (runs, artifacts, triage, work_items)
CLI: run --output DIR → files under DIR only (no Postgres)
X5:  import_json (sample / CLI export / history) → Postgres (idempotent)
FE → /api/v1 → Postgres
```

---

## Historical CURRENT notes (pre-B1) — archived context

The following bullets described HEAD before B1 and are retained only as audit trail. They are **not** CURRENT after B1.

<details>
<summary>Pre-B1 endpoint table (removed)</summary>

Legacy unversioned routes and subprocess `/run` — deleted in B1.

</details>

### Adapters / settings (still partially CURRENT)

- Conversation path uses `AISettings` (`OPSPILOT_AI_*` with `ANTHROPIC_API_KEY` fallback).
- Evening / insights / briefing / claude adapters still read env / hardcode model (gateway is B2).
- Factory honors `OPSPILOT_FORCE_RULES` so tests never construct Anthropic for **triage**. Until B2 gateway, FORCE_RULES is **triage-factory-only** — evening/insights/briefing/conversation paths do not yet honor it (see runbooks).

### Data flow (files + DB)

```
sample_input.json → pipeline → data/output (latest) + data/history/runs/...
Frontend fetch → FastAPI → adapters / file reads
```

No database. Settings overrides are in-memory only.

### Known defects (selected)

| ID | Issue |
|----|-------|
| V1–V3 | Non-hermetic / order-dependent tests; subprocess + missing package init |
| V4 / SEC-01 | Unauthenticated settings key mutation (deploy gate) |
| V5 | Vitest installed; zero FE tests |
| V6 | briefing_adapter wrong attribute names |
| V7 | npm audit / no TS `strict` |
| AI-01… | Duplicated LLM plumbing; no gateway resilience/evals |
| AI-05 | TriageRecord lacks real title/subject |

Full audit: [docs/audits/2026-09-25-baseline-audit.md](audits/2026-09-25-baseline-audit.md).

---

## TARGET

### Package layout + dependency rules (D-024)

Keep `src/opspilot/` + `frontend/` (D-022). TARGET tree (principal-review §2.1):

```
src/opspilot/
  __init__.py
  api/
    app.py
    deps.py
    errors.py                 # single error envelope
    v1/
      routes_health.py
      routes_runs.py
      routes_triage.py
      routes_ask.py           # + SSE
      routes_drafts.py
      routes_prefs.py
      routes_admin.py         # settings read-only
  domain/
    models.py
    enums.py
  services/
    triage_service.py
    briefing_service.py
    ask_service.py
    sync_service.py
    draft_service.py
    preference_service.py
  llm/
    gateway.py
    types.py
    routing.py
    budgets.py
    prompts/
    providers/
      gemini.py
      groq.py
      ollama.py
      anthropic.py            # prepaid gated only
  agent/
    loop.py
    tools/
      search_items.py
      get_message.py
      get_calendar.py
      draft_reply.py
      send_reply.py
    events.py
  integrations/
    google_oauth.py
    gmail_client.py
    calendar_client.py
  persistence/
    db.py
    repositories/
    migrations/               # Alembic
  jobs/
    morning_run.py
    sync_mail.py
  evals/
    datasets/
    metrics/
    runners/
  obs/
    tracing.py
    metrics.py
  config/
    settings.py               # env-only secrets
  rules/
    triage_rules.py
```

**Dependency rules:**

- `api` → `services` → (`domain`, `llm`, `agent`, `integrations`, `persistence`)
- `agent` → `llm` + read services; never `integrations.send` without approval service
- `evals` may use `rules` + LLM fakes; never load `.env` keys in CI lane
- `integrations` must not import `api`
- No upward imports from `llm` into `api`
- Provider SDKs only inside `llm/providers/`

### Domain model (minimum)

| Entity | Key fields | Relationships |
|--------|------------|---------------|
| **User** | id, email, google_sub, role=`demo_operator`\|`visitor` | 1:n runs, prefs |
| **WorkItem** | id, source, subject, body, sender, received_at, thread_id, provider_id **unique**, raw_json | n:1 Thread |
| **Thread** | id, subject, participants | 1:n WorkItems |
| **TriageDecision** | urgency, category, sentiment, reasons, **confidence**, **evidence_refs**, model, prompt_version | n:1 WorkItem |
| **Commitment** | text, due_at, status | DEFER table OK empty |
| **Meeting** | calendar_event_id, start, end, title, attendees | |
| **Draft** | work_item_id, body, status=`pending`\|`approved`\|`sent`\|`rejected` | |
| **Approval** | draft_id, user_id, decided_at, decision | |
| **Preference** | key, value, source=`user_correction` | |
| **Feedback** | triage_decision_id, correct_label?, note, promoted_to_eval | |
| **Run** | kind=`morning`\|`manual`\|`sync`, status, started_at, stats | |
| **LlmCall** | task, provider, model, latency_ms, ttft_ms, tokens_in/out, USD fields, prompt_version, status | |
| **DemoMailbox** | fictional account binding (operator-only) | |
| **SyncCursor** | provider sync checkpoints (X1) | |

### API `/api/v1`

- Prefix: **`/api/v1`**
- Error envelope: `{ "error": { "code": str, "message": str, "details": object|null } }`
- Auth: session cookie (HTTP-only) after Google OAuth for operator; visitor = read-only demo, no Google link
- Rate limit: per IP + per user on LLM routes
- Streaming: `POST /api/v1/ask/stream` → `text/event-stream`
- Settings: `GET /api/v1/settings` **read-only** (no keys); **no** key PATCH

**Current → future map**

| Current | Future |
|---------|--------|
| `GET /health` | `GET /api/v1/health` (+ `GET /api/v1/ready` checks DB) |
| `GET/PATCH /api/settings` | `GET /api/v1/settings` read-only; **remove PATCH** |
| `POST /run` | `POST /api/v1/runs` (in-process; no subprocess) |
| `GET /briefing`, `/ai-briefing` | `GET /api/v1/briefings/latest` |
| `GET /triage` | `GET /api/v1/triage` |
| `GET /runs*` | `GET /api/v1/runs`, `.../{id}` |
| `POST /ask` | `POST /api/v1/ask` + `/ask/stream` |
| `POST /evening-summary` | `POST /api/v1/evening-summary` |
| `POST /insights` | `POST /api/v1/insights` |
| `GET /inputs` | remove or admin-only |
| `GET /capabilities*` | keep as product roadmap UI or static |

### LLM gateway + Anthropic prepaid gate (D-012, D-023)

```text
complete(task, messages, schema=None) -> Result
stream(task, messages) -> AsyncIterator[Event]
```

**Default order:** `gemini → groq → ollama → rules` (task-dependent). Anthropic **never** in the default list.

- **Failover:** on 429/5xx/timeout; honor Retry-After; circuit open N minutes
- **Budgets:** daily req/token caps per free provider from env; Anthropic hard **token and USD** remaining (D-023)
- **Structured output:** native JSON schema/mode → Pydantic; retry once; fail closed
- **Prompts:** `llm/prompts/{name}/v{N}.md` + sha256 in `LlmCall`
- **Tracing:** `obs.tracing` + persist `LlmCall`
- Anthropic: enable flag + allowlisted tasks only; never tests/CI; never visitor Ask (D2/D11)

### Agent loop + approval boundary (D-014)

- Tools as JSON schemas; allowlist in config: `search_items`, `get_message`, `get_calendar`, `draft_reply`, `send_reply`
- Max steps (e.g. 5), max wall time, max tokens
- Read-only tools until approve&send; `send_reply` requires approved `approval_id`
- SSE events: `token`, `tool_start`, `tool_end`, `final`, `error`
- DEMO_MODE visitors cannot send

### Eval lanes (D-018) + amendment

| Lane | When | Anthropic? |
|------|------|------------|
| Deterministic | Always CI | No |
| Local model | CI optional / nightly | No |
| Hosted free | Manual / weekly | No |
| Prepaid quality | Operator, budgeted | Yes, gated |
| Judge calibration | Manual subset | Optional gated |

Datasets under `evals/datasets/` (fictional). Metrics: precision/recall/F1, confusion matrix, groundedness (ID citation), judge score. Injection red-team shares the **same harness** (B3). ASR tracked in CI.

### Security

- Secrets: env / host secret store only; FE never sees keys
- Auth: Google OAuth operator; visitors anonymous read-only
- Injection: system prompt policy + **untrusted-content delimiters** around email bodies + CI red-team ASR
- PII: fictional policy; if detector fires → **Ollama-only** path
- X2 HMAC `POST /api/v1/jobs/morning` — **B7 optional** only (D-011); B6 does not need public webhook
- Rate limits before public (B7)
- DEMO_MODE blocks send for visitors

### Frontend

- React Router; **standardize panels** to conditional mount + shared `useOverlay` (X8 in B5)
- Fetch + React state (D-020); TanStack Query only if cache pain appears
- SSE: EventSource or fetch stream reader in AskPanel
- PWA out of spine; Telegram link in settings for operator
- Types: OpenAPI-lite generated/checked in CI (X7 in B1)
- B1 exits: TS `strict` on; minimal vitest in CI; react-router upgraded (`npm audit --omit=dev` 0 high)

### Jobs / scheduling

**CURRENT:** Manual CLI/API only; no in-app scheduler. Local Windows Task Scheduler remains a valid **dev** path.

**TARGET B6 (D-011):** GitHub Actions cron runs `morning_run` **inside the runner** (install package; GHA secrets for Gemini/Groq, Neon URL, Telegram token, token-encryption key; Google refresh token read encrypted from Neon). Writes Neon; notifies Telegram. **No public backend** before B7. Fail fast if Neon schema ≠ Alembic head; migrations are operator-applied, never by cron. Auth failure → skip sync, brief from existing data, Telegram re-auth alert.

**TARGET B7:** Public deploy; optional HMAC webhook wake of deployed API (X2).

### Deployment topology

```mermaid
flowchart LR
  Visitor[VisitorBrowser]
  FE[PagesClassFE]
  BE[RenderClassBE]
  Neon[(NeonPostgres)]
  Gemini[GeminiAPI]
  Groq[GroqAPI]
  Gmail[DemoGmailCalendar]
  GHA[GitHubActionsCron]
  Tg[TelegramBot]
  Dev[Developer]
  Ollama[OllamaLocal]

  Visitor --> FE
  FE --> BE
  BE --> Neon
  BE --> Gemini
  BE --> Groq
  BE --> Gmail
  GHA -->|"B6 in-runner write"| Neon
  GHA -->|"B6 notify"| Tg
  GHA -->|"B7 optional HMAC"| BE
  Dev --> Ollama
  Dev --> BE
```

No custom domain. Anthropic only via operator budgeted scripts, not visitor path. Ollama is **local/CI only** — not wired from deployed BE.

### Deliberately simple

No LangGraph, LiteLLM, Celery, Qdrant, visitor BYOK, multi-tenant beyond operator vs visitor, LoRA, MCP client, or custom domain in the locked spine.
