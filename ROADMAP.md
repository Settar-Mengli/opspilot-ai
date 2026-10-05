# OpsPilot Roadmap

**Status:** Locked spine **B0–B7** (2026-09-26). Former M0–M10 are workstreams **inside** batches — scope and exit criteria preserved.

**Principles:** Zero further spend · fictional demo data · CURRENT vs TARGET grounding · one branch per batch (`bN/...`) · Ask→Plan→Build · Plan requirements in [AGENTS.md](AGENTS.md).

Master record: [OPSPILOT-MASTER-RECORD.md](OPSPILOT-MASTER-RECORD.md) · Architecture: [docs/architecture.md](docs/architecture.md) · ADRs: [docs/adr/](docs/adr/)

**Global exit rule (every batch):** **Tests** · **Evals** (if any) · **Live smoke** · **Docs** (master-record PART appended after merge rule; ROADMAP / ADRs / CHANGELOG updated).

---

## Batch map (B0–B7 ↔ former M0–M10)

| Batch | Contains | Goal |
|-------|----------|------|
| **B0** | M0 | Docs & architecture lock |
| **B1** | M1 | Hermetic foundation + Postgres + SEC + `/api/v1` |
| **B1.5a** | UI hygiene | UI safety net + overlay primitive + U4 fixes |
| **B1.5b** | UI desktop | Desktop three-pane layout from design-reference |
| **B2** | M2 | LLM gateway + trace hooks (+ Anthropic prepaid gate) |
| **B2.1** | Hardening | Hardening + truth (docs/toolchain/security/obs) |
| **B3** | M3 + M4 | Eval platform + injection red-team on **one harness** |
| **B3.1** | Live remainder | CF D5 + combined done; OpenRouter **partial** D6 only (D7–D9/D10 cancelled) |
| **B4** | M5 | Demo Google inbox/calendar |
| **B5** | M6 + M7 | Agentic Ask + SSE + approve & send |
| **B6** | M8 + M9 | Morning run (in-runner) + Telegram + preferences → evals |
| **B7** | M10 | Public free-tier deploy |

**Order:** B0 → B1 → **B1.5a → B1.5b** → B2 → **B2.1** → B3 → B4 → **B3.1** → B5 → B6 → B7.

*(Planned spine listed B3.1 before B4; **executed** order was B3 then B4 then B3.1 per owner lock.)*

**X-item placement (one batch each):**

| X | Placement |
|---|-----------|
| X1 sync idempotency | **B4** |
| X2 optional HMAC manual trigger | **B7** |
| X3 DEMO_MODE introduced | **B4** (B5 exit must enforce DEMO_MODE on send) |
| X4 prompt/data minimization | **B0** AGENTS + **B2** gateway |
| X5 JSON→DB importer | **B1** |
| X6 Anthropic guard in tests | **B1** |
| X7 OpenAPI-lite + FE types with `/api/v1` | **B1** |
| X8 panel lifecycle | **Started B1.5a** (`useOverlay`; `PortalOverlay` introduced then removed in `32fc6e1` unused); agent Ask surfaces finish on **B1.5b layout in B5** |

**Anthropic amendment:** gate in **B2**; optional leaderboard column in **B3**; prod disabled-by-default at **B7**.

---

## Locked spine B0–B7

### B0 — Documentation & architecture lock (M0 / F3)

- **Goal:** Lock plan in-repo before code rebuild.
- **Workstream M0**
  - **Scope:** Master record PART 0–2, ADRs, architecture rewrite, AGENTS/CONTRIBUTING/README, roadmap, runbooks, doc retire/merge, LICENSE holder; B0 fix pass.
  - **Exit criteria:**
    - **Tests:** n/a (docs only); pytest/lint/build still green as regression.
    - **Evals:** n/a.
    - **Live smoke:** n/a for docs; key check False.
    - **Docs:** PART 2 accepted; CUT/DEFER frozen; docs+LICENSE only on branch; **merged** to `main`.
- **Deps:** none · **Size:** M–L · **Metric:** Architecture & roadmap locked in-repo

### B1 — Hermetic foundation, Postgres, SEC gate & /api/v1 reshape (M1)

- **Status:** Merged to `main` via PR #2 (`c5de149`, 2026-09-26).
- **Goal:** Honest CI, Postgres persistence (local/CI Compose; Neon deferred), safe settings, versioned API with one error envelope.
- **Workstream M1** — F1a + V1–V7 critical + D-008/D-009 + X5 + X6 + X7 + O3
  - **Scope:**
    - Package hygiene: `src/opspilot/__init__.py`; in-process pipeline (no subprocess CLI for `/run`).
    - Neon Postgres + SQLAlchemy 2 + Alembic; CI Postgres service (no SQLite); local Postgres strategy chosen in B1 plan (Docker vs Neon branch).
    - X5 JSON→DB importer for sample/history data.
    - `/api/v1` reshape with single error envelope `{ "error": { "code", "message", "details" } }`; current→future route map from architecture; OpenAPI-lite + generated/checked frontend types (X7).
    - Env-only secrets; Settings **read-only** (no API-key PATCH); remove non-functional OpenAI option (SEC-01 / AI-02).
    - Hermetic tests (fake LLM, tmp dirs); Anthropic client never constructed in tests (X6); fix V6 briefing attrs.
    - Lockfile; ruff + mypy + coverage gates with numeric thresholds set in B1 plan.
    - Align CI Python to a single supported version (document 3.11 vs 3.13 choice in B1 plan; exit = CI and local both green on that choice).
    - FE: upgrade react-router (clear npm audit H/M); enable TS `strict`; minimal vitest suite in CI (≥1 smoke test file).
    - gitleaks + Dependabot enabled as CI/repo gates.
    - Begin reshaping toward D-024 package layout as needed for `/api/v1` + persistence.
  - **Exit criteria:**
    - **Tests:**
      - `pytest -q` green, including when run alone and in random order (`test_get_triage` isolated).
      - A network-blocking test fixture makes any outbound HTTP fail the suite; the suite stays green with an Anthropic key present in `.env` (X6).
      - ruff, mypy, and coverage pass in CI at the thresholds fixed in the B1 plan.
      - Alembic upgrade → downgrade → upgrade round-trip passes on CI Postgres.
      - The X5 importer is idempotent: running it twice yields identical row counts.
      - `npm run lint`, `npm run build` (TS strict), and vitest pass in CI.
      - `npm audit --omit=dev` shows 0 high.
      - gitleaks is clean on the PR; Dependabot config is present.
    - **Security:**
      - `PATCH /api/settings` is removed (405/404); `GET` is read-only with no key material.
      - The Settings UI has no API-key input and no `openai` option.
    - **API:**
      - The frontend calls `/api/v1` exclusively; legacy routes are removed or listed as deprecated in the route map.
      - An invalid request returns the error envelope `{error:{code,message,details}}`.
      - OpenAPI-lite frontend types are generated or checked in CI.
    - **Evals:** n/a (B3).
    - **Live smoke:**
      - Boot the API against local Postgres; import sample data.
      - `GET /api/v1/health` → 200; `GET /api/v1/triage` returns the imported items from Postgres; one invalid request returns the envelope.
      - The frontend dashboard renders from `/api/v1`.
    - **Docs:** master-record PART appended; ROADMAP, ADRs, and CHANGELOG updated.
- **Deps:** B0 · **Size:** XL · **Metric:** Hermetic CI; $0 test runs; `/api/v1` + Postgres live

### B1.5a — UI safety net & hygiene

- **Status:** Delivered via PR #18 (`b1.5a/ui-safety-net`; C-BASE + owner approval 2026-09-27).
- **Goal:** Playwright visual/e2e/axe safety net; CSS split; shared overlay primitive; U4 bug fixes; D-026/D-027.
- **Scope:** Container-only `-linux` baselines; migrate Notify→Ask onto `useOverlay`; U4 (subject_or_title, gear label, CSS token aliases, triage/evening errors, safe-area, Sample badges); F-06 importer path jail; deprecate `api.main`.
- **Exit:** UI Tests green in pinned Playwright image; docs PART 4 + ADRs; live smoke per plan.
- **Deps:** B1 · **Size:** XL · **Metric:** 0-diff hygiene + named U4 baseline updates

### B1.5b — Desktop three-pane layout

- **Status:** Merged to `main` (PR #29).
- **Goal:** ≥1280 three-pane (rail + content + docked Ask 380px) from `frontend/design-reference/` (D-026).
- **Scope:** Desktop layout only; phone ≤768 stays pixel-locked except owner-approved changes; agent Ask chrome lands here for B5 to finish X8 agent surfaces. FUTURE (B5) streaming/tools/HITL not built.
- **Exit:** Mockups + gallery approved; 1280 baselines refreshed; `B15B_DESKTOP_HOLD` removed (E11: 0 matches in hold implementation paths `.github`/`frontend`; historical doc mentions by design); PART 6 (incl. E2 deviation record).
- **Non-blocking follow-ups (next UI-touching batch):** NB-3 Connections modal dialog ARIA/`tabIndex={-1}`; NB-4 All Items error state when triage fails.
- **Deps:** B1.5a · **Size:** L · **Metric:** Approved desktop mocks shipped with baseline updates

### B2 — LLM gateway + traces (M2)

- **Goal:** Multi-provider free path + metering hooks.
- **Workstream M2** — A1 + A4 hooks + X4 in gateway
  - **Scope:** Hand-rolled gateway under `llm/` (D-012/D-024); Gemini/Groq/Ollama (+ mistral/cloudflare/openrouter); migrate remaining adapters; structured outputs; prompt versions; LlmCall traces; **Anthropic prepaid gate** (D-023); daily free-tier quotas; 429/Retry-After failover; prompt/data minimization (X4); services layer; runs pagination; request_id; timestamptz (D-027).
  - **Exit criteria:**
    - **Tests:** Fake-provider unit tests; budget=0 or disabled → no Anthropic HTTP; allowlisted+budget mocked path allowed; CI never constructs Anthropic client; 429/Retry-After failover covered; LlmCall rows written in tests with fakes; ask/evening/insights soft-200 shapes.
    - **Evals:** n/a (B3) except smoke hooks if any.
    - **Live smoke:** Free provider happy path via Invoke-RestMethod; optional Anthropic budgeted script (not CI).
    - **Docs:** PART 7; ROADMAP/ADRs/CHANGELOG; free-tier quotas VERIFY AT DECISION TIME noted.
- **Status:** Merged to `main` (PR #30 → `0c71a4a`). Quotas approved 2026-09-29; C12 + S1–S4 + F8–F9 in PART 7.
- **Deps:** B1 · **Size:** XL · **Metric:** Multi-provider gateway with failover

### B2.1 — Hardening + truth

- **Status:** Merged to `main` (PR #32 → `7501b9e`, 2026-09-30). PART 8 recorded.
- **Goal:** Post-B2 hardening: register truth-align, toolchain pins, security redaction/OpenRouter/:request-id, dead-code delete, observability, expand-only index, portfolio docs. API shapes unchanged; 0 PNG changes.
- **Exit:** Full pytest ≥72% (baseline 81.19%); greps clean; PART 8; Dependabot ignores for TS7 / @types/node≥25 / Playwright until U9.
- **Deps:** B2 · **Size:** L · **Metric:** Hardening + honest CURRENT docs

### B3 — Eval platform + injection red-team (M3 + M4) — one harness

- **Status:** Merged to `main` (PR #36 → `3eb7baf`, 2026-09-30). Hermetic F1-FLOOR **0.30**; D1–D3 full + CF D4 **partial 33/60**; CF/OR pre-closeout smokes **passed**. Live remainder → **B3.1**. PART 9 complete.
- **Goal:** Regression + jailbreak/injection defense on a single eval harness.
- **Workstream M3** — A2 + P8 phase1 lite
  - **Scope:** Labeled fictional corpus; F1/confusion; item-ID grounding + confidence on triage; CI secret-free lane; Anthropic column documented `skipped` (P7; no Anthropic HTTP in B3).
  - **Exit criteria (M3):** CI gate fails on triage regression beyond conservative threshold owner-locked at STOP F1-FLOOR.
- **Workstream M4** — A3 lite
  - **Scope:** Delimiters; red-team suite on **same harness**; hermetic defense tests in CI; **live ASR reported per provider (not a CI gate)** (P8 / D-029).
  - **Exit criteria (M4):** Known attack fixtures fail closed hermetically; ASR + validity/repair published in `docs/evals/`.
- **Batch exit criteria:**
  - **Tests:** M3 F1 gate + M4 hermetic defenses green.
  - **Evals:** Golden F1 + live red-team ASR as above (partial CF documented; remainder completed in B3.1 with OR partial).
  - **Live smoke:** Multi-day single-provider leaderboard under approved caps (STOP LIVE); remainder completed in B3.1.
  - **Docs:** PART 9; ROADMAP/ADRs/CHANGELOG updated.
- **Deps:** B2 · **Size:** XL · **Metric:** Triage F1 on golden set; red-team ASR live-reported

### B3.1 — Live leaderboard remainder (CF D5 + OpenRouter D6 partial)

- **Status:** Merged to `main` (PR #39 → `1a6fe7d`). **No new product scope.**
- **Delivered:**
  - Pre-live guards (checkpoint, case selection, local-DB refuse, per-case commit, `--max-requests`); `LAST_GUARD_SHA` `0a4f5d5`.
  - **Cloudflare D5** + **CF combined** (60/60; F1 0.706 n=40; ASR 0.150 3/20).
  - **OpenRouter D6** triage `001`–`015` only (F1 0.619 n=15; ASR N/A — red-team not run).
- **Owner amendment (D-B31-4, 2026-10-01):** OpenRouter D7–D9/D10 + required OR combined artifact **cancelled** to unblock **B5**. Remainder → OPTIONAL backlog (no owner batch).
- **Exit:** Leaderboard CURRENT; PART 12; CHANGELOG; next **B5**.
- **Deps:** B3 · B4 · **Size:** S · **Metric:** CF complete + OR partial published (Anthropic still skipped)

### B4 — Demo Google inbox/calendar (M5)

- **Status:** Merged to `main` (PR #37 → `c6e677c`, 2026-10-01). STOP LIVE passed (Neon); PART 10 + PART 11 closeout.
- **Goal:** Live fictional inbox/calendar for operator demo.
- **Workstream M5** — P1 + X1 + X3 + D-016
  - **Scope:** OAuth Testing forever; sync + idempotency (X1); replace JSON default path; WeekPanel from calendar; **DEMO_MODE** introduced (X3); encrypted refresh token in Neon; weekly re-auth runbook.
  - **Exit criteria:**
    - **Tests:** Sync idempotency tests; DEMO_MODE flag tests; no visitor OAuth path. **DONE** (hermetic).
    - **Evals:** n/a or reuse B3 corpus on synced fictional items.
    - **Live smoke:** **DONE** — Connect + Sync + capped triage 50/50; WeekPanel live meetings; G1–G7 fixed forward.
    - **Docs:** PART 10; D-016/D-030 final; ROADMAP Open findings; CHANGELOG.
- **Deps:** B1 persistence, B2 gateway, B3 before agent reads bodies · **Size:** XL · **Metric:** Live fictional inbox demo
- **Next after merge:** B3.1 (done — see above), then **B5** (done — see B5), then **B6**.

### B5 — Agentic Ask + approve & send (M6 + M7) — **DONE**

- **Goal:** Tool-using Ask with HITL send.
- **Workstream M6** — P2 + X8 — **DONE**
  - Bounded JSON-emulated tool loop (D-031); caps 5/8 (D-014); `POST /ask/stream` SSE (D-032); read tools + `draft_reply`; Ask dock/timeline/draft card.
- **Workstream M7** — P3 + X3 — **DONE**
  - `gmail.send` scope; HITL edit/approve; allowlist fail-closed; DEMO_MODE 403; Gmail reply-in-thread only; `mail_send_audit`.
- **Also IN:** Gmail `messageDeleted` + SPAM/TRASH label removal; history/list + Calendar pagination with safe cursors; DM-09 `ttft_ms` on Ask SSE; hermetic `ask_agent` + `redteam_agent` evals; reality-gap fix-pass (PART 13).
- **Batch exit:** hermetic gates green; ask-error visual refresh (**gallery approved** 2026-10-02); Neon Alembic **0009**; PART 13; **live_smoke_b5 PASS** 2026-10-02 (1 real send).
- **Merged:** PR #40 → `2131f32` (merge CI [37070730054](https://github.com/Settar-Mengli/opspilot-ai/actions/runs/37070730054) success). Tip fill `9957cf4` push/PR CI in PART 15.
- **Deps:** B2–B4 · **Size:** XL · **Next:** **B6** (done — see B6)

### B6 — Morning run + preferences (M8 + M9) — **DONE**

- **Goal:** Scheduled brief + human feedback into evals — **in-runner**, no public backend (D-011).
- **Merged:** PR #44 → `eae1a9a` (merge CI [37263038965](https://github.com/Settar-Mengli/opspilot-ai/actions/runs/37263038965) success). Alembic **0010** on `main` / applied on Neon by owner (PART 15). PART 14–17 (branch) + PART 18 (merge closeout).
- **Workstream M8** — P4 + P11-telegram — **DONE**
  - **Scope:** GHA cron in-runner; morning triage/brief; Telegram notify; schema-head check; fail-closed auth (D-016).
  - **CURRENT on main:** Sync 202/poll drain; morning_run + Telegram counts-only; C14 schedule `0 12 * * *` + `workflow_dispatch` in `.github/workflows/morning.yml` (workflow **active**). First `event=schedule` run on `main` **pending** at PART 18 closeout.
  - **Exit criteria (M8):** Cron smoke writes Neon + Telegram; no public BE required; auth-fail path alerts re-auth. **Owner LIVE PASS 2026-10-04** (PART 15) — GHA LLM triage proven (run 37247296563); reauth drill + restore; send count unchanged. Schedule YAML on default branch via merge.
- **Workstream M9** — P5 lite — **partial**
  - **Scope:** Correction UI; Preference store; promote to eval dataset.
  - **CURRENT on main:** Corrections overlay + brief upsert onto latest gmail `run_id`; in-memory `promotion_hook` (unit-tested). Ask-agent dataset has 7 cases (`n_cases=7`).
  - **Exit criteria (M9):** One correction appears in eval dataset path.
  - **M9 remainder (deferred / open):** `promotion_hook` → eval dataset file write / preference promotion **not** in locked W1–W10; track under M9/OPTIONAL or next owner batch (fix-pass PART 16).
- **Batch exit criteria:**
  - **Tests:** Job unit tests with fakes; preference→eval path tested (in-memory hook).
  - **Evals:** Promoted case appears in harness path — **open** (M9 remainder).
  - **Live smoke:** Manual workflow_dispatch succeeded; Telegram received. **LIVE PASS** recorded (dispatch). First scheduled cron on `main` pending observation.
  - **Docs:** PART 14–18; ROADMAP/CHANGELOG/architecture/runbook truth-aligned.
- **Deps:** B3, B4/B5 as needed for data · **Size:** L–XL · **Metric:** Scheduled morning brief; feedback → eval cases · **Next:** **B7** (owner-pending order may insert Anthropic/MCP PR first — PART 18)

### B7 — Public free-tier deploy (M10)

- **Goal:** Public demo URL without custom domain.
- **Workstream M10** — F2 + X2
  - **Scope:** Docker; Pages-class FE + Render-class BE + Neon; rate limits; retention; README metrics; `OPSPILOT_ANTHROPIC_ENABLED=false` unless capped operator demo; **optional HMAC** manual trigger (X2). Deploy env must **not** set `OPSPILOT_FORCE_RULES` (tests/CI only).
  - **Exit criteria:**
    - **Tests:** Deploy smoke script / health checks.
    - **Evals:** n/a.
    - **Live smoke:** Public URL; sleep-tolerant; visitors cannot select Anthropic; DEMO_MODE enforced.
    - **Docs:** PART appended; ROADMAP/ADRs/CHANGELOG updated.
- **Deps:** B1–B6 spine quality bar · **Size:** XL · **Metric:** Public free-tier demo URL

---

## Open findings (deferred; owner-batch rows unless marked OPTIONAL)

| Item | Owner batch | Notes |
|------|-------------|-------|
| M9 `promotion_hook` → eval dataset file write / preference promotion | **M9/OPTIONAL** | In-memory hook + unit tests on main; file write not in locked W1–W10 (PART 16) |
| F-01 authn/authz on public `/api/v1` | **B7** | Operator cookie is local-demo only (D-030) |
| F-02 HTTP rate limiting | **B7** | |
| F-13 disable `/docs` in public deploy | **B7** | |
| OBS-2 `/ready` DB check | **B7** | |
| OpenRouter leaderboard completion (triage 016–040 + red-team 20) | **OPTIONAL** | Unassigned; D-B31-4 amended 2026-10-01 (OR stopped at D6 to unblock B5) |
| Dependabot majors: Playwright 1.63, lucide, TypeScript 7, Vitest 5 | **deps+U9** | Dedicated baseline refresh batch |
| OD-1 / OD-2 / OD-3 / OD-5 / OD-6 (contrast, focus rings, fonts, axe) | **OD** | Owner-approved OD batch with U9 |
| D-007 `?run_id=` deep-link + RUNS FE paging | **deps+U9** | OUT of B5; D-007 status updated |
| `generated.ts` unused (hand-written client) | **deps+U9** | OUT of B5 |
| Duplicate `getTriage` fetches | **OD** | OUT of B5 |
| FE code splitting | **deps+U9** | OUT of B5 |
| `complete_json` path split / dual gateway loops | **deps+U9** | OUT of B5; agent uses BudgetAwareGateway |
| CQ-04 soft-deny user-visible copy unification | **OD** | OUT of B5 |
| F-11 token cap ≤1-call overshoot | **deps+U9** | OUT of B5 |
| DM-09 `ttft_ms` / `usd_estimate` / LlmCall links | **partial** | **ttft_ms on Ask SSE in B5**; `usd_estimate` + prepaid ledger plumbing on main (B6); Anthropic still off |
| F-05 Anthropic USD debit on LlmCall | **B7** | Plumbing on main (B6); precondition before Anthropic ever enabled (P7 off) |
| Connections 768 Gmail card subtitle orphan word (cosmetic) | **OD** | Owner-noted after gallery approval 2026-10-02; not a defect; not a merge gate |
| Ask chose a non-latest, third-party item when asked for “the latest inbox mail” (observed in live smoke Run 2) — add an Ask eval case | **eval/OPTIONAL** | Smoke script fixed (`6eef4c4`); ask_agent case landed in B6 (`n_cases=7`); product Ask targeting quality deferred to eval |

---

## Post-B7 optional (former M11–M15) + backlog

| Former | Item | Trigger |
|--------|------|---------|
| M11 | P9 FTS → semantic | Real corpus size |
| M12 | P6 commitments | After HITL send proven |
| M13 | P7 meeting prep | After calendar sync quality |
| M14 | Phoenix UI | After LlmCall hooks prove value |
| M15 | A5 distill / LoRA | After evals + teacher quality |

Also deferred: MCP client, attachments/vision, full PWA+push, **P10 multilingual (DEFER)**, LiteLLM/LangGraph/Celery/Qdrant, visitor BYOK, custom domain.

---

## Out of scope / rejected near-term

- Paid API spend beyond existing Anthropic prepaid
- Publishing Google OAuth beyond Testing / visitor Gmail connect
- Training a model from scratch
- Cloning the other portfolio repo’s LangGraph/RAG/Celery stack
- Public backend before B7
