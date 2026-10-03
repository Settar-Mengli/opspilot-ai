# B6 delta pre-audit — 2026-10-03

Ask-mode evidence against `main` @ `2131f32` (PR #40 B5 merge). Claims below are **CURRENT** only where verified in code; planned behaviour is **TARGET**.

## Verdict table (F1–F14)

| ID | Claim | Verdict | Evidence |
|----|--------|---------|----------|
| F1 | `run_pipeline` holds one `llm_session_scope` across classify + both briefings; one run per call; triage unique `(work_item_id, run_id)`; untriaged = no decision row | CONFIRMED | `run_daily_ops.py:78–107`; `_llm.py:106–108`; `models.py:91–93`; `work_items.py:89–97` |
| F2 | Each call writes briefing over that batch only; UI latest = max artifact id | CONFIRMED | `run_daily_ops.py:88–107`; `routes.py:104–117` |
| F3 | `execute_pipeline` waits 120s then abandons worker | CONFIRMED | `paths.py:9`; `pipeline.py:44–78` |
| F4 | POST `/sync`: DEMO + cookie; no CSRF; commit sync then capped triage | CONFIRMED | `oauth_routes.py:112–123`; CSRF only on disconnect |
| F5 | Single uvicorn, no reload, no lifespan; no job table | CONFIRMED | `run_api.py:9–14`; `app.py:84–115` |
| F6 | Only advisory lock = `pg_advisory_xact_lock` send-cap | CONFIRMED | `mail_hitl.py:47–54` |
| F7 | Engine `pool_pre_ping` only; Neon label ends `-pooler` | CONFIRMED | `db.py:54–55`; master-record PART |
| F8 | Neon pooler = PgBouncer transaction mode | OWNER-VERIFIED external (2026-10-03) | Design for pooled URL |
| F9 | Briefings embed titles, action summaries, owners | CONFIRMED | `briefing_generator.py:30–57`; `briefing_adapter.py:64–85` |
| F10 | Draft statuses; failed not re-approvable; unknown/unavailable → draft | CONFIRMED | `mail_drafts.py:14`; `mail_hitl.py` |
| F11 | Anthropic stripped; not in `build_providers`; usd in `raw` not recorded | CONFIRMED | `routing.py`; `anthropic.py:158`; `gateway.py:247–260` |
| F12 | Visual fixture `google_connected:false`; no Sync/draft; detail pane desktop-only | CONFIRMED | `settings.json:6`; `helpers.ts`; `AllItemsPage.tsx:151–160` |
| F13 | No preference/job/Telegram/schedule; Alembic head `0009_…`; F1 floor 0.30 | CONFIRMED | `test_alembic_roundtrip.py:52`; triage manifest; `rules_baseline.py:12` |
| F14 | Stale B5-unmerged docs; PART 13 tip placeholder for `9957cf4` | CONFIRMED | `architecture.md:22`; git; master-record |

## Also verified

| Topic | Evidence |
|-------|----------|
| Briefing reader gmail filter | `routes.py:104–117` |
| Latest triage readers | `routes.py:69–101,273–318`; `routes_ask.py:44–71` |
| Approve non-draft → 409 | `mail_hitl.py:140–141` |
| LLM timeout / Retry-After / providers | `http.py:10–15`; `routed.py`; `routing.py:16` |
| `DATABASE_URL` / encryption / Google client env | `db.py:23`; `crypto.py:15`; `google_oauth.py:75–84` |
| Successful send count helper | `mail_send_audit.py:51–70` |
| `complete_structured` soft-catch | `_llm.py:181–190` |
| Pytest baseline | Owner **475** on main (Build re-measures); PART tip 463 historical |
| Coverage | CI `--cov-fail-under=72` |

## Gaps closed by B6 (TARGET)

| Gap | B6 workstream |
|-----|---------------|
| No morning job / Telegram notify | W1, W2 |
| Sync holds request through capped triage (G6) | W3, W4 |
| No durable job / lease under pooler | W1, D-034 |
| No operator corrections overlay | W5, D-035 |
| Failed drafts not reopenable | W6 |
| F-05 usd / prepaid ledger unwired | W9 (Anthropic still disabled) |
| Docs/ROADMAP stale vs B5 tip | W10 |

## Non-goals (confirmed)

- Public auth F-01, HMAC, `/ready` → B7
- Celery / queues
- Send as an agent tool
- Anthropic enablement (D-023 unchanged for enablement)
- OpenRouter leaderboard completion; MCP; visitor BYOK
