# OpsPilot Roadmap

**Status:** Locked spine **B0–B7** (2026-09-26). Former M0–M10 are workstreams **inside** batches — scope and exit criteria preserved.

**Principles:** Zero further spend · fictional demo data · CURRENT vs TARGET grounding · one branch per batch (`bN/...`) · Ask→Plan→Build.

Master record: [OPSPILOT-MASTER-RECORD.md](OPSPILOT-MASTER-RECORD.md) · Architecture: [docs/architecture.md](docs/architecture.md) · ADRs: [docs/adr/](docs/adr/)

---

## Batch map (B0–B7 ↔ former M0–M10)

| Batch | Contains | Goal |
|-------|----------|------|
| **B0** | M0 | Docs & architecture lock |
| **B1** | M1 | Hermetic foundation + SEC gate |
| **B2** | M2 | LLM gateway + trace hooks (+ Anthropic prepaid gate) |
| **B3** | M3 + M4 | Eval platform + injection red-team on **one harness** |
| **B4** | M5 | Demo Google inbox/calendar |
| **B5** | M6 + M7 | Agentic Ask + SSE + approve & send |
| **B6** | M8 + M9 | Morning run + Telegram + preferences → evals |
| **B7** | M10 | Public free-tier deploy |

**Order:** B0 → B1 → B2 → B3 → B4 → B5 → B6 → B7.

**X-item placement:** X6 Anthropic-guard → B1; X1 sync idempotency → B4; X3 DEMO_MODE → B4/B5; X2 cron HMAC → B6; X4 minimization → B0 AGENTS + B2; X5 JSON→DB importer → B1/B4; X7 OpenAPI lite → B1 or B5; X8 panel lifecycle → B5.

**FE folds:** vitest + TS strict + router hygiene → B1 trajectory; panel lifecycle + SSE AskPanel → B5.

**Anthropic amendment:** gate in **B2**; optional leaderboard column in **B3**; prod disabled-by-default at **B7**.

---

## Locked spine B0–B7

### B0 — Documentation & architecture lock (M0 / F3)

- **Goal:** Lock plan in-repo before code rebuild.
- **Workstream M0**
  - **Scope:** Master record PART 0–2, ADRs, architecture rewrite, AGENTS/CONTRIBUTING/README, roadmap, runbooks, doc retire/merge, LICENSE holder.
  - **Exit:** Owner accepts PART 2; CUT LIST frozen; docs+LICENSE only on branch.
- **Deps:** none · **Size:** M–L · **Metric:** Architecture & roadmap locked in-repo

### B1 — Hermetic foundation & SEC gate (M1)

- **Goal:** Honest CI and safe local settings.
- **Workstream M1** — F1a + V1–V7 critical
  - **Scope:** In-process pipeline; `src/opspilot/__init__.py`; env-only settings (no key PATCH); hermetic tests (fake LLM, tmp dirs); Anthropic-guard in tests (X6); fix V6; lockfile; ruff+mypy+coverage started; gitleaks/Dependabot trajectory.
  - **Exit:** `pytest` alone green; `test_get_triage` isolated; **zero** real LLM calls in default suite.
- **Deps:** B0 · **Size:** XL · **Metric:** Hermetic CI; $0 test runs
- **Note:** Local Postgres (Docker vs Neon branch) chosen in B1 plan (D-008).

### B2 — LLM gateway + traces (M2)

- **Goal:** Multi-provider free path + metering hooks.
- **Workstream M2** — A1 + A4 hooks
  - **Scope:** Hand-rolled gateway; Gemini/Groq/Ollama; migrate remaining adapters; structured outputs; prompt versions; LlmCall traces; **Anthropic prepaid gate** (D-023).
  - **Exit:** Fake-provider unit tests; live smoke on Gemini **or** Ollama; Anthropic disabled/budget=0 → no HTTP; allowlisted+budget mocked path allowed; CI never constructs Anthropic client.
- **Deps:** B1 · **Size:** XL · **Metric:** Multi-provider gateway with failover

### B3 — Eval platform + injection red-team (M3 + M4) — one harness

- **Goal:** Regression + jailbreak/injection defense on a single eval harness.
- **Workstream M3** — A2 + P8 phase1 lite
  - **Scope:** Labeled fictional corpus; F1/confusion; item-ID grounding + confidence on triage; CI secret-free lane; optional Anthropic prepaid leaderboard column.
  - **Exit:** CI gate fails on triage regression beyond conservative threshold.
- **Workstream M4** — A3 lite
  - **Scope:** Delimiters; red-team suite on **same harness**; ASR tracked in CI.
  - **Exit:** Known attack fixtures fail closed.
- **Batch exit:** Both M3 and M4 exits pass.
- **Deps:** B2 · **Size:** XL · **Metric:** Triage F1 on golden set; red-team ASR tracked

### B4 — Demo Google inbox/calendar (M5)

- **Goal:** Live fictional inbox/calendar for operator demo.
- **Workstream M5** — P1 + X1 + D-016
  - **Scope:** OAuth Testing forever; sync + idempotency (X1); replace JSON default path; WeekPanel from calendar; DEMO_MODE (X3).
  - **Exit:** Live smoke on demo account; visitors never OAuth mail.
- **Deps:** B1 persistence, B2 gateway, B3 before agent reads bodies · **Size:** XL · **Metric:** Live fictional inbox demo

### B5 — Agentic Ask + approve & send (M6 + M7)

- **Goal:** Tool-using Ask with HITL send.
- **Workstream M6** — P2
  - **Scope:** Bounded tool loop; multi-turn caps; SSE; **read-only tools first**; panel lifecycle (X8).
  - **Exit:** Smoke: ask → tool → grounded answer; quota budget enforced.
- **Workstream M7** — P3 + X3
  - **Scope:** Draft UI; approval; Gmail send; audit row; DEMO visitors blocked from send.
  - **Exit:** Cannot send without approval.
- **Commit sequence inside batch:** read-only tools → then approval boundary + send.
- **Deps:** B2–B4 · **Size:** XL · **Metric:** Tool-using Ask with streaming; HITL send path

### B6 — Morning run + preferences (M8 + M9)

- **Goal:** Scheduled brief + human feedback into evals.
- **Workstream M8** — P4 + P11-telegram + X2
  - **Scope:** GHA cron; morning triage/brief; Telegram notify; cron HMAC (X2).
  - **Exit:** Cron smoke; HMAC required.
- **Workstream M9** — P5 lite
  - **Scope:** Correction UI; Preference store; promote to eval dataset.
  - **Exit:** One correction appears in eval dataset path.
- **Deps:** B3, B5 (or minimal public URL for cron) · **Size:** L–XL · **Metric:** Scheduled morning brief; feedback → eval cases

### B7 — Public free-tier deploy (M10)

- **Goal:** Public demo URL without custom domain.
- **Workstream M10** — F2
  - **Scope:** Docker; Pages-class FE + Render-class BE + Neon; rate limits; retention; README metrics; `OPSPILOT_ANTHROPIC_ENABLED=false` unless capped operator demo.
  - **Exit:** Public URL; sleep-tolerant; visitors cannot select Anthropic.
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

Also deferred: MCP client, attachments/vision, full PWA+push, multilingual (P10), LiteLLM/LangGraph/Celery/Qdrant, visitor BYOK, custom domain.

---

## Out of scope / rejected near-term

- Paid API spend beyond existing Anthropic prepaid
- Publishing Google OAuth beyond Testing / visitor Gmail connect
- Training a model from scratch
- Cloning the other portfolio repo’s LangGraph/RAG/Celery stack
