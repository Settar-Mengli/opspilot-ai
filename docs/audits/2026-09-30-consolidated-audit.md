# Consolidated Audit Register — 2026-09-30

**Repo:** github.com/Settar-Mengli/opspilot-ai · **Audited:** `main` @ `5933685` (after B2 merge `0c71a4a`, DEP-2 `aa5c73d`, Dependabot #21/#22/#25/#27)
**Mode:** seven read-only Ask-mode audits run in separate Cursor sessions, consolidated here by the owner.
**Sources:** comprehensive B3 pre-audit · security · architecture & code quality · frontend/UX/a11y · portfolio & hiring readiness · B4, B5, B6, B7 draft pre-audits.
**Status:** this file is the decision record. Full per-audit evidence (path:line, command output) lived in the Cursor sessions; the key evidence is carried into each finding below.

---

## 1. Verdicts

| Audit | Verdict |
|---|---|
| Comprehensive (main health) | **HEALTHY WITH FIXES** — 149 tests, 81.11% coverage, mypy/ruff clean, Alembic head `0004_timestamptz`, CI run 36657422313 green, 0 open PRs, 0 Dependabot alerts |
| Comprehensive (B3 readiness) | **READY WITH PRE-WORK** — records drift + toolchain first |
| Security | Credible for **local-only** use; **not ready for public exposure** (B7); injection + redaction gaps before real mail (B4) |
| Architecture | B2 gateway sound; D-024 layering incomplete; dual gateway loops; observability holes; no seams yet for B3–B7 |
| Frontend | **Conditionally healthy** — one live soft-200 UX bug, NB-3/NB-4 open, OD debt |
| Portfolio | **Conditional shortlist** — strong engineering, but README is stale (pre-B2) and has no proof (badges, screenshots, demo, metrics) |
| B4 / B5 / B6 / B7 drafts | **NOT READY** — each depends on the batches before it (order B3 → B4 → B5 → B6 → B7). Kept as planning drafts; a short delta check replaces a full re-audit when each batch is next |

---

## 2. Findings register and dispositions

Dispositions: **B2.1** = hardening + truth batch before B3 · **B3** · **UI** = next UI batch (with B4) · **B4–B7** · **DEFER** · **REJECT**.

### 2.1 Records / docs drift

| ID | Finding | Evidence | Disposition |
|---|---|---|---|
| R-1 | README describes pre-B2 product ("Next: B1.5… then B2", gateway "not yet", Claude-first) | `README.md:5,12,19,24` | B2.1 |
| R-2 | ROADMAP: B1.5b "PR open; not merged", B2 "PR #30 open" | `ROADMAP.md:113,130` | B2.1 |
| R-3 | architecture.md: "B2 on branch until merge"; live caps need STOP A | `docs/architecture.md:3,20,28` | B2.1 |
| R-4 | PART 7 summary still "awaiting owner merge"; no merge SHA recorded | `OPSPILOT-MASTER-RECORD.md:494` | B2.1 — record the merge in a new PART 8 (PART 7 is closed / append-only) |
| R-5 | CHANGELOG missing Dependabot merges #21/#22/#25/#27 | `CHANGELOG.md` | B2.1 |
| R-6 | ROADMAP M4 says "ASR tracked in CI" — conflicts with lock P8 | `ROADMAP.md` B3 | B3 (amend with P8) |
| R-7 | D-004 text outdated; D-007 `?run_id=` not implemented in FE | ADRs vs `frontend/src` | B2.1 (D-004 addendum); D-007 → UI batch decision |
| R-8 | Baseline audit "AI score 2/5" is pre-B2 | `docs/audits/2026-09-25-baseline-audit.md:35` | B2.1 — add post-B2 note in README/docs, do not rewrite the audit |

### 2.2 Toolchain

| ID | Finding | Disposition |
|---|---|---|
| T-1 | jsdom 30 needs Node ^24.15; `.nvmrc` = 24, engines `>=24 <25`, local 24.14 (EBADENGINE) | B2.1 — Node ≥24.15 in `.nvmrc`, engines, CI |
| T-2 | `ubuntu-latest` migrates to Ubuntu 26 from 2026-10-19 (VERIFY AT DECISION TIME) | B2.1 — pin non-container jobs to `ubuntu-24.04`; keep Playwright container pin |
| T-3 | Dependabot has no ignore rules; TS7 / @types/node 26 / Playwright majors reopened | B2.1 — ignore TypeScript ≥7, @types/node ≥25 (engines), Playwright/@playwright until U9 batch |

### 2.3 Security

| ID | Sev | Finding | Evidence | Disposition |
|---|---|---|---|---|
| F-01 | Critical at B7 | No authn/authz on any `/api/v1` route | `routes.py` | B4 (operator auth) / B7 |
| F-02 | High | No HTTP rate limiting | `app.py` | B7 |
| F-03 | High | Indirect prompt injection: bodies in `<item>` without untrusted policy | `gateway_triage.py:48–55`; `ask.py:30–33` | B3 (P8 delimiters + defenses) |
| F-04 | High | `meta_redact`/`sanitize_meta` bypass: nested dicts, Bearer JWTs, `AIza…`, `cf_token=` survive into JSONL / `llm_calls.meta` (verified by probe) | `meta_redact.py:15–61`; `logging_utils.py:24–25` | **B2.1** — recursive sanitize + expanded patterns + tests |
| F-05 | Med | D-023 Anthropic LlmCall USD debit not implemented; `usd_estimate` never set | `anthropic.py:52–79`; `gateway.py:243–256` | DEFER — required before Anthropic is ever enabled (P7 keeps it off) |
| F-06 | Med | OpenRouter `:free` not enforced at runtime | `model_defaults.py`; `openai_compatible.py` | **B2.1** — reject non-`:free` unless explicit paid flag |
| F-07 | Med | `GET /triage` unbounded | `routes.py:136–139` | B4 (paginate / cap with data growth) |
| F-08 | Med | `X-Request-ID` accepted unsanitized | `app.py:28–29` | **B2.1** — ≤64 chars, `[A-Za-z0-9._-]`, else regenerate |
| F-09 | Med | `logger.exception` on LLM failures may log provider snippets | `_llm.py:105–106,137–138` | **B2.1** — log error_code + redacted text only |
| F-10 | Med | Ruleset requires 0 approving reviews | ruleset 24045198 | **REJECT** — sole author cannot approve own PRs; required checks + no force-push/deletion remain |
| F-11 | Low | Token cap can overshoot by ≤1 call under concurrency | `routed.py:330–345`; `budgets.py:94–95` | DEFER — 80% cap margin covers it; documented |
| F-12 | Low–Med | `frontend/.env.example` contains `ANTHROPIC_API_KEY` placeholder | `frontend/.env.example` | **B2.1** — remove; FE never holds keys |
| F-13 | Low | FastAPI `/docs` enabled | `app.py:41–45` | B7 |
| F-14/15 | Low | `/settings` exposes `api_key_set`; `AISettings.override` footgun | `routes.py:88–90`; `settings.py:110–127` | B4 (settings redesign, NB8) |
| OK | — | Errors sanitized; localhost bind + CORS; DB-down fail-closed; path traversal blocked; Actions SHA-pinned; `contents: read`; no `pull_request_target` | various | keep |

### 2.4 Architecture / code quality / observability / tests

| ID | Finding | Disposition |
|---|---|---|
| L-01 | Routes import ORM directly (skip services) | B4 — thin repositories before data growth |
| L-03/L-04/L-05 | Triage/briefing still `pipeline → adapters`; adapters import services | B2.1 partial (move briefing to services if cheap) / B4 |
| CQ-03, CQ-09, CQ-10 | Dead code: `claude_adapter`, `evening_adapter`, `insights_adapter`, `conversation_adapter` (tests only), `domain/models.py` (0 importers, 0% coverage) | **B2.1** — delete, retarget tests |
| CQ-02 | Dual failover loops (`LlmGateway` vs `BudgetAwareGateway`) | B2.1 if low-risk (document skeleton-only) else DEFER |
| CQ-04 | Policy deny and provider failure produce the same soft copy | DEFER to UI batch (user-visible text) |
| CQ-05/06 | Duplicated provider HTTP error mapping; duplicated soft-deny order | B2.1 (internal refactor, no behavior change) |
| CQ-01 | `BudgetAwareGateway.complete_json` ~148 LOC hotspot | DEFER (B3 touches it; split when needed) |
| OBS-1 | `request_id` not passed for triage/briefing; ContextVar never read; unhandled 500s not logged; no access log | **B2.1** |
| OBS-2 | No `/ready` DB check | B7 |
| DM-03 | No index on `run_artifacts.name` (hot read) | B2.1 (expand-only migration) or B4 |
| DM-09 | `ttft_ms`, `usd_estimate`, `run_id`, `work_item_id` never written on LlmCall | DEFER (B5 ttft; F-05 USD) |
| TQ-01..04 | Weak soft-path asserts; circuit expiry untested; `json_extract` edges; OR-asserts in `meta_redact` tests | **B2.1** |
| CQ-13 | Provider `stream()` = complete-then-one-chunk | B5 |

### 2.5 Frontend / UX / a11y

| ID | Finding | Disposition |
|---|---|---|
| F-INS | **Live bug:** Insights soft-200 `{intro, insights:[]}` renders hardcoded empty copy, discarding `intro` | `InsightsPage.tsx:87–91` | UI batch (first UI-touching commit; prefer 0-PNG copy swap) |
| NB-4 | All Items swallows triage errors (`catch(console.error)`) | UI batch |
| NB-3 + C13 | Connections modal lacks dialog semantics/focus trap; `.cn-cat` not keyboard-operable | UI batch (with B4 Connections work) |
| GEN | `generated.ts` has zero imports; hand-written `client.ts`/`types.ts` | DEFER (wire when API grows) |
| RUNS | `limit`/`cursor` unused in FE | B4+ |
| DUP | `getTriage` fetched 4× | DEFER |
| OD-1/2/5/6 | Contrast, focus rings, self-host fonts, axe waiver | Owner OD batch with U9 baseline refresh |
| OD-3 | Fake observation timestamps | UI batch or OD batch |
| PW163 | Playwright 1.63 + lucide need full baseline refresh | Dedicated deps + U9 batch |
| PERF | Single 320 kB JS chunk, no code splitting | DEFER |

### 2.6 Portfolio

| ID | Finding | Disposition |
|---|---|---|
| P-1 | README truth-align + proof pack: badges, 2–3 screenshots from existing `-linux` baselines, AI-stack section with paths, architecture diagram, honest "not yet" | **B2.1** |
| P-2 | `docs/design-decisions.md` linking key ADRs (D-011/012/013/018/019/023/025/026) | **B2.1** |
| P-3 | GitHub topics + description (owner runs `gh repo edit`) | B2.1 owner step |
| P-4 | Issue/PR templates | B2.1 |
| P-5 | Eval numbers (F1, validity, live ASR) | B3 |
| P-6 | Demo video/GIF | after B3 (Loom) and after B5 (agentic) |
| P-7 | Public link | B7 |
| Rule | Never claim metrics not in-repo (no invented F1/latency/users) | standing |

---

## 3. B3 owner locks (reviewed and agreed by the comprehensive audit)

| Lock | Final wording |
|---|---|
| P1 | Synthetic fictional corpus, N=40, `evals/datasets/triage/v1/`, `label_version=triage-labels/v1`, append-only; B6 promotion hook reserved |
| P2 | Primary: macro-F1 (unweighted mean of urgency/category/sentiment F1) + structured validity%. Leaderboard adds repair%, p50/p95 latency, tokens/case; confusion matrices as artifacts |
| P3 | `src/opspilot/evals/` + `tests/evals/`; CLI `python -m opspilot.jobs.run_evals` (hermetic default, `--live` owner-gated); results JSON + markdown in `docs/evals/`; no eval DB table |
| P4 | Scorer has exact unit tests (FakeProvider is not a quality gate). Hermetic regression gate = rules classifier vs labels; floor measured in-batch, owner-locked at STOP F1-FLOOR. Prompt-construction snapshot tests. Threshold changes only via explicit PR commits |
| P5 | Live leaderboard: owner-gated, BudgetAwareGateway, exactly one provider per run (no failover), multi-day where caps bind; publish `docs/evals/leaderboard.md` + JSON; no UI |
| P6 | No LLM-as-judge in B3 |
| P7 | Anthropic column documented as `skipped` (zero-spend); no Anthropic HTTP in B3 |
| P8 | Hermetic tests verify defenses (untrusted delimiters, neutralized fake closers/role spoofs, enum-only labels, output guard on reasons, schema strictness). Live ASR reported per provider (not a CI gate). ~20 attacks in `evals/datasets/redteam/v1/`. ROADMAP M4 wording amended |
| P9 | Ollama: local runbook only; no CI job |
| P10 | NB9 folded into the first live leaderboard (per-provider validity/repair) |
| P11 | `_BODY_MAX = 500` |
| P12 | `confidence` + `evidence_refs` in TriagePayload + nullable DB columns (expand-only migration + round-trip); not in API/UI; deterministic grounding check `evidence_refs ⊆ allowed ids` |
| P13 | `temperature=0` for structured tasks only (triage, insights, eval); prose keeps provider defaults |

**Live schedule (planning at 1.5×, 40 triage + ~20 attacks = 60 cases/provider):** D1 Gemini · D2 Groq · D3 Mistral · D4–D5 Cloudflare (80 req/day) · D5–D7 OpenRouter (40 req/day). Confirm counter headroom each UTC day (STOP LIVE). Provider limits VERIFY AT DECISION TIME.

---

## 4. Key design notes carried forward (B4–B7 drafts)

| Batch | Decisions to lock when the batch is next |
|---|---|
| B4 | OAuth auth-code + PKCE, Web client with loopback redirect; Testing mode forever (D-016); scopes `gmail.readonly` + `calendar.readonly` only (send deferred to B5); Fernet-encrypted refresh token in `bytea` (D-027), key in env/secrets; opaque WorkItem id + unique `provider_id`; SyncCursor (historyId / syncToken); headers + text only, attachments ignored; DEMO_MODE flag introduced; Neon provisioned; NB-3/NB-4/F-INS in the same UI work; STOP GOOGLE-SETUP, STOP LIVE |
| B5 | Tool capability map (native / JSON-emulated / unsupported, verified per provider); SSE as an agent event stream (buffered LLM completes first); 5-step cap + per-turn call cap; exact-payload approval with server-side hash; DEMO_MODE blocks sends; Gmail reply only (calendar writes deferred); STOP NATIVE TOOLS, STOP LIVE, STOP VISUAL |
| B6 | In-runner GHA cron (D-011); owner TZ → UTC with DST documented; one morning run per UTC day; Telegram plain/HTML, summary-only (X4), `TELEGRAM_CHAT_ID` secret; soft budget reserve for the morning run; fail-closed brief when OAuth refresh expired (~7-day Testing expiry — VERIFY); corrections → eval cases without silent threshold drift; STOP SECRETS, STOP LIVE |
| B7 | D-021 stack (Cloudflare Pages + Render + Neon), VERIFY free tiers at account time; visitors see DEMO data only; per-IP + global rate limits + kill switch; Anthropic off; `/docs` disabled; security headers; `/ready`; Dockerfile; FE base-URL allowlist fix (`client.ts:16–37` currently rejects non-localhost); STOP ACCOUNTS, STOP DEPLOY, STOP PUBLIC |

---

## 5. Batch order (owner-approved sequence)

1. **B2.1 — Hardening + truth** (backend/docs/toolchain; API shapes unchanged; 0 PNG changes)
2. **B3 — Evals + red-team** (locks P1–P13)
3. **B4 — Gmail + Calendar** (+ first UI batch items: F-INS, NB-4, NB-3/C13)
4. **B5 — Agentic Ask**
5. **B6 — Morning run + Telegram**
6. **B7 — Public deploy**
7. Separate owner-approved **deps + U9 baseline batch** (Playwright 1.63, lucide, TS7, Vitest 5) and **OD batch** (OD-1/2/3/5/6), scheduled around UI work.

## 6. Rejected / deferred with reasons

| Item | Decision | Reason |
|---|---|---|
| F-10 require 1 PR approval | Rejected | Sole author; GitHub blocks self-approval; required checks already gate merges |
| F-05 Anthropic USD debit | Deferred | Only needed if Anthropic is enabled; precondition recorded |
| Hermetic ASR gate | Rejected | FakeProvider cannot be injected; defenses tested hermetically, ASR measured live (P8) |
| FakeProvider F1 floor as quality gate | Rejected | Tests only the scorer (P4) |
| Ollama CI job | Deferred | Runner cost/flakiness (P9) |

## Corrections (B2.1 plan verification)

Verified against `main` @ `5933685` (CI run 36657422313) during B2.1 plan authoring.

| ID / claim | Correction |
|---|---|
| Coverage "81.11%" | CI reports **Total coverage: 81.19%** (149 passed). Use **81.19%** as the B2.1 baseline floor-to-explain. |
| F-04 evidence paths | Canonical paths: `src/opspilot/llm/meta_redact.py`, `src/opspilot/utils/logging_utils.py`. |
| CQ-05 | Duplication is specifically `openai_compatible.py` + `gemini.py` HTTP status→`ProviderResult` mapping (other free providers inherit OpenAI-compatible). |
| CQ-06 "identical strings" | Soft **copy is per-surface** (ask ≠ evening ≠ insights). B2.1 shared helper preserves each surface's **current** strings and the shared deny **order** (`llm_allowed` → no-provider → unavailable). Do **not** unify user-visible copy (CQ-04 remains UI/DEFER). |
| L-03/L-04/L-05 "B2.1 partial move briefing" | **Out of B2.1** per owner scope. Briefing stays in adapters; repository/services move deferred. Dead-adapter deletes (CQ-03/09/10) remain in B2.1. |
| PART 7 NB3 → B2.1 | Superseded: triage `_BODY_MAX` change is **B3** (lock P11 = 500), not B2.1. |
| Dependabot #23/#24/#26/#28 | Verified CLOSED: #23 lucide-react, #24 @playwright/test→1.63, #26 @types/node→26, #28 typescript→7. Merged: #21, #22, #25, #27. |
| DM-03 | Hot name-only queries confirmed at `routes.py` GET `/briefing` and `/ai-briefing`; **kept in B2.1** as expand-only `0005`. |

All other B2.1 dispositions in §2 remain CONFIRMED.
