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
| **B3** | M3 + M4 | Eval platform + injection red-team on **one harness** |
| **B4** | M5 | Demo Google inbox/calendar |
| **B5** | M6 + M7 | Agentic Ask + SSE + approve & send |
| **B6** | M8 + M9 | Morning run (in-runner) + Telegram + preferences → evals |
| **B7** | M10 | Public free-tier deploy |

**Order:** B0 → B1 → **B1.5a → B1.5b** → B2 → B3 → B4 → B5 → B6 → B7.

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
| X8 panel lifecycle | **Started B1.5a** (`useOverlay` / `PortalOverlay`); agent Ask surfaces finish on **B1.5b layout in B5** |

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
    - **Docs:** PART 2 accepted; CUT/DEFER frozen; docs+LICENSE only on branch; PR open.
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

- **Status:** Build complete on `b1.5a/ui-safety-net` (C-BASE + owner approval 2026-09-27; PR next).
- **Goal:** Playwright visual/e2e/axe safety net; CSS split; shared overlay primitive; U4 bug fixes; D-026/D-027.
- **Scope:** Container-only `-linux` baselines; migrate Notify→Ask onto `useOverlay`; U4 (subject_or_title, gear label, CSS token aliases, triage/evening errors, safe-area, Sample badges); F-06 importer path jail; deprecate `api.main`.
- **Exit:** UI Tests green in pinned Playwright image; docs PART 4 + ADRs; live smoke per plan.
- **Deps:** B1 · **Size:** XL · **Metric:** 0-diff hygiene + named U4 baseline updates

### B1.5b — Desktop three-pane layout

- **Goal:** ≥1280 three-pane (rail + content + docked Ask) from `frontend/design-reference/` (D-026).
- **Scope:** Desktop layout only; phone ≤768 stays pixel-locked except owner-approved changes; agent Ask chrome lands here for B5 to finish X8 agent surfaces.
- **Deps:** B1.5a · **Size:** L · **Metric:** Approved desktop mocks shipped with baseline updates

### B2 — LLM gateway + traces (M2)

- **Goal:** Multi-provider free path + metering hooks.
- **Workstream M2** — A1 + A4 hooks + X4 in gateway
  - **Scope:** Hand-rolled gateway under `llm/` (D-012/D-024); Gemini/Groq/Ollama; migrate remaining adapters; structured outputs; prompt versions; LlmCall traces; **Anthropic prepaid gate** (D-023); daily free-tier quotas; 429/Retry-After failover; prompt/data minimization (X4).
  - **Exit criteria:**
    - **Tests:** Fake-provider unit tests; budget=0 or disabled → no Anthropic HTTP; allowlisted+budget mocked path allowed; CI never constructs Anthropic client; 429/Retry-After failover covered; LlmCall rows written in tests with fakes.
    - **Evals:** n/a (B3) except smoke hooks if any.
    - **Live smoke:** Gemini **or** Ollama happy path; optional separate Anthropic budgeted script (not CI).
    - **Docs:** PART appended; ROADMAP/ADRs/CHANGELOG updated; free-tier quotas VERIFY AT DECISION TIME noted.
- **Deps:** B1 · **Size:** XL · **Metric:** Multi-provider gateway with failover

### B3 — Eval platform + injection red-team (M3 + M4) — one harness

- **Goal:** Regression + jailbreak/injection defense on a single eval harness.
- **Workstream M3** — A2 + P8 phase1 lite
  - **Scope:** Labeled fictional corpus; F1/confusion; item-ID grounding + confidence on triage; CI secret-free lane; optional Anthropic prepaid leaderboard column.
  - **Exit criteria (M3):** CI gate fails on triage regression beyond conservative threshold set in B3 plan.
- **Workstream M4** — A3 lite
  - **Scope:** Delimiters; red-team suite on **same harness**; ASR tracked in CI.
  - **Exit criteria (M4):** Known attack fixtures fail closed; ASR metric published in CI artifact/docs.
- **Batch exit criteria:**
  - **Tests:** Both M3 and M4 automated gates green.
  - **Evals:** Golden F1 + red-team ASR as above.
  - **Live smoke:** Optional hosted free leaderboard run documented.
  - **Docs:** PART appended; ROADMAP/ADRs/CHANGELOG updated.
- **Deps:** B2 · **Size:** XL · **Metric:** Triage F1 on golden set; red-team ASR tracked

### B4 — Demo Google inbox/calendar (M5)

- **Goal:** Live fictional inbox/calendar for operator demo.
- **Workstream M5** — P1 + X1 + X3 + D-016
  - **Scope:** OAuth Testing forever; sync + idempotency (X1); replace JSON default path; WeekPanel from calendar; **DEMO_MODE** introduced (X3); encrypted refresh token in Neon; weekly re-auth runbook.
  - **Exit criteria:**
    - **Tests:** Sync idempotency tests; DEMO_MODE flag tests; no visitor OAuth path.
    - **Evals:** n/a or reuse B3 corpus on synced fictional items.
    - **Live smoke:** Live smoke on demo account; visitors never OAuth mail; re-auth runbook exercised once.
    - **Docs:** PART appended; ROADMAP/ADRs/CHANGELOG; D-016 constraints recorded.
- **Deps:** B1 persistence, B2 gateway, B3 before agent reads bodies · **Size:** XL · **Metric:** Live fictional inbox demo

### B5 — Agentic Ask + approve & send (M6 + M7)

- **Goal:** Tool-using Ask with HITL send.
- **Workstream M6** — P2 + X8
  - **Scope:** Bounded tool loop; multi-turn caps; SSE; **read-only tools first**; finish X8 agent Ask surfaces on the **B1.5b** desktop layout (overlay primitive already landed in B1.5a).
  - **Exit criteria (M6):** Smoke ask → tool → grounded answer; quota budget enforced.
- **Workstream M7** — P3 + X3 enforce
  - **Scope:** Draft UI; approval; Gmail send; audit row; **DEMO_MODE blocks send** for visitors.
  - **Exit criteria (M7):** Cannot send without approval; DEMO visitors blocked from send.
- **Commit sequence inside batch:** read-only tools → then approval boundary + send.
- **Batch exit criteria:**
  - **Tests:** Tool loop + approval + DEMO_MODE send denial.
  - **Evals:** Regression suite still green.
  - **Live smoke:** Tool-using Ask with streaming; HITL send on operator account only.
  - **Docs:** PART appended; ROADMAP/ADRs/CHANGELOG updated.
- **Deps:** B2–B4 · **Size:** XL · **Metric:** Tool-using Ask with streaming; HITL send path

### B6 — Morning run + preferences (M8 + M9)

- **Goal:** Scheduled brief + human feedback into evals — **in-runner**, no public backend (D-011).
- **Workstream M8** — P4 + P11-telegram
  - **Scope:** GHA cron in-runner; morning triage/brief; Telegram notify; schema-head check; fail-closed auth (D-016).
  - **Exit criteria (M8):** Cron smoke writes Neon + Telegram; no public BE required; auth-fail path alerts re-auth.
- **Workstream M9** — P5 lite
  - **Scope:** Correction UI; Preference store; promote to eval dataset.
  - **Exit criteria (M9):** One correction appears in eval dataset path.
- **Batch exit criteria:**
  - **Tests:** Job unit tests with fakes; preference→eval path tested.
  - **Evals:** Promoted case appears in harness path.
  - **Live smoke:** Manual workflow_dispatch or scheduled run succeeds; Telegram received.
  - **Docs:** PART appended; ROADMAP/ADRs/CHANGELOG; [gha-morning-job.md](docs/runbooks/gha-morning-job.md) current.
- **Deps:** B3, B4/B5 as needed for data · **Size:** L–XL · **Metric:** Scheduled morning brief; feedback → eval cases

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
