# OpsPilot AI — Non-UI Systems Audit

**Target:** `main` @ `c5de149` (B0+B1 merged). **Ask mode — no writes.**  
**Excluded:** Frontend UI (separate audit).  
**Tags:** **VERIFIED** / **INFERRED** / **VERIFY AT DECISION TIME**

---

## 0. Verdict + top 15 findings

**Verdict:** B1 delivered a credible hermetic foundation (sync Postgres, `/api/v1` envelope, CI gates, D-010/D-025). Docs and ROADMAP still describe B1 as unmerged. The AI layer remains pre-gateway (direct Anthropic SDKs, inconsistent `AISettings`/`FORCE_RULES`), which is the main B2 risk and the main zero-spend leak surface. Schema can absorb B2–B6 tables if conventions are locked now. Highest leverage before B2: **docs merge-status cleanup**, **FORCE_RULES / settings unification across all LLM sites**, **`LlmCall` conventions ADR**, and **test gaps on ask/evening/insights**.

| Rank | ID | Finding | Severity |
|------|-----|---------|----------|
| 1 | C-01 | `OPSPILOT_FORCE_RULES` only gates triage factory; evening/insights/briefing/conversation still construct Anthropic | **Critical** |
| 2 | C-02 | Four adapters hardcode `ANTHROPIC_API_KEY` + model; only conversation uses `AISettings` | **High** |
| 3 | A-01 | Docs still say B1 “pending merge” / PR open (architecture, README, ROADMAP, PART 3 branch line) | **High** |
| 4 | B-01 | `api/v1/routes` imports adapters directly — violates D-024 `api → services → llm` | **High** |
| 5 | B-02 | `GET /api/v1/runs` unbounded (no pagination/limit) | **High** |
| 6 | D-01 | No API tests for `/ask`, `/evening-summary`, `/insights` (live spend risk if socket escapes) | **High** |
| 7 | E-01 | CI Actions pinned by tag (`@v4`/`@v5`), no `permissions:` block; no pip-audit | **High** |
| 8 | C-03 | Claude triage sends full work-item **body** into prompts (X4) | **High** |
| 9 | G-01 | Timestamps mixed (`String` vs `DateTime(timezone=True)`); no schema conventions ADR for B2+ | **High** |
| 10 | A-02 | `docs/audits/*` whitespace-only drift vs `ab5b5ee` (459c644); history untouched | **Medium** *(B1.5-c1)* |
| 11 | B-03 | No request IDs; unstructured logs; auto-commit every request | **Medium** |
| 12 | F-01 | Validation `details=exc.errors()` can leak schema internals; CORS local-only (OK pre-B7) | **Medium** |
| 13 | B-04 | Dead/compat surface: `api/main.py` re-exports; `domain/models.py` only re-exports ORM | **Medium** |
| 14 | H-01 | B2 blocked until gateway + LlmCall + adapter migration map executed | **Medium** |
| 15 | I-01 | README first screen still points at `b1/hermetic-foundation` branch | **Medium** |

---

## 1. Section A — Records & docs accuracy

| ID | Sev | Evidence | Impact | Fix | Owner batch |
|----|-----|----------|--------|-----|-------------|
| **A-01** | High | `docs/architecture.md:3` “branch `b1/hermetic-foundation` (pending merge)”; `README.md:5–6`; `ROADMAP.md:61` “PR open”; `OPSPILOT-MASTER-RECORD.md:251` same | Reviewers/agents treat B1 as unfinished | Rewrite CURRENT to `main` @ c5de149; mark B1 merged | **docs-only chore** |
| **A-02** | Medium | `git diff --numstat ab5b5ee HEAD -- docs/audits` equal ± lines; `git diff -w` empty (**VERIFIED** whitespace-only). `docs/history` commit count `ab5b5ee..HEAD` = **0** | Audit corpus no longer byte-identical; MD soft-breaks stripped by 459c644 | Restore from `ab5b5ee`; exclude audits/history from EOF/whitespace hooks | **B1.5-commit-1 chore** |
| **A-03** | Medium | PART 3 Q4/Q6/A3 accurate for sync DB / D-025 / fail_under 72 (`OPSPILOT-MASTER-RECORD.md:260–266`) but branch status stale (`:251`) | Partial truth | Fix branch/status line; after merge, append PART 4 for later corrections (append-only rule `:15`) | **docs-only chore** |
| **A-04** | Low | `CHANGELOG.md:12` B1 bullets match CURRENT; still under `[Unreleased]` | Fine until release tag | Optional “Merged B1” note | **docs-only chore** |
| **A-05** | Medium | README/local-dev uv + Compose + alembic (**VERIFIED** `README.md:32–45`, `docs/runbooks/local-dev.md` patterns). Not executed this session | Commands look Windows-correct **INFERRED** | Operator smoke once post-doc fix | **docs-only chore** |
| **A-06** | Low | AGENTS commit gates match tooling (ruff/mypy/pytest/pre-commit) | OK | Keep | — |
| **A-07** | Low | D-008 addendum Compose/CI (**VERIFIED**); D-010 revised sync; D-025 CLI files-only; D-009 Alembic RT — match code | OK | — | — |
| **A-08** | Low | Master-record “While B0 is unmerged” (`:15`) obsolete | Confusing append-only policy text | Clarify B0/B1 merged | **docs-only chore** |

---

## 2. Section B — Backend architecture & code quality

### D-024 conformance (**VERIFIED**)

| Present | Missing / wrong |
|---------|-----------------|
| `api/` (`app`, `deps`, `errors`, `v1/`), `persistence/`, `jobs/`, thin `domain/` | No `llm/`, `services/` (only `api/services/`), `agent/`, `integrations/`, `evals/`, `obs/` |
| | **`routes.py` → adapters`** (`routes.py:14–16`) skips service layer |
| | `adapters/` still top-level (TARGET: under `llm/` post-B2) |
| | `domain/models.py` re-exports ORM rows only (`domain/models.py:1–15`) |

| ID | Sev | Evidence | Impact | Fix | Owner |
|----|-----|----------|--------|-----|-------|
| **B-01** | High | `routes.py:14–16,194–221` | Harder B2 gateway insertion; upward coupling | Introduce `services/ask.py` etc.; routes call services only | **B2** |
| **B-02** | High | `list_runs` `select(RunRow).order_by...` no limit (`routes.py:108–112`) | Memory/DoS as history grows | `limit`/`cursor` query params; default 50 | **B2** or small **docs-only** defer with cap in B1.5 if cheap |
| **B-03** | Medium | `deps.py:24–32` commit-on-success every request; `logging_utils.py:10–19` plain text, no request_id | Opaque prod debug; long transactions on ask+LLM | Middleware request_id; shorter sessions for read paths | **B2** / **B7** |
| **B-04** | Medium | `api/main.py:1–10` compat re-export; `paths.py` still used for `RAW_INPUT_DIR` | Mild confusion | Keep `RAW_INPUT`; deprecate `main.py` entry in docs | **B1.5** / **docs-only** |
| **B-05** | Low | `history/run_history.py` still used by CLI pipeline (`run_daily_ops.py` imports) | Coherent for CLI files path (D-025) | Keep until file history retired | — |
| **B-06** | Medium | `started_at`/`finished_at`/`received_at` as `String(64)` (`models.py:25–36`); only `created_at` is `DateTime(timezone=True)` (`:43–47`) | Sort/filter bugs; TZ ambiguity | Prefer timestamptz everywhere going forward | **B2** (+ ADR) |
| **B-07** | Low | N+1: triage join is one query (`routes.py:57–60`) **VERIFIED** OK | — | — | — |
| **B-08** | Medium | Pool: `pool_pre_ping=True` only (`db.py:31–32`); no size/timeouts | Fine for local; VERIFY for Neon | Document Neon pool settings | **B4**/**B7** |
| **B-09** | Low | Input validation: Ask max 2000 (`schemas.py:42–48`); `resolve_input_file` blocks `..` (`:111–115`) | Good | Add global body size limit at ASGI | **B7** |
| **B-10** | Low | Env: `.env.example` has AI keys + DATABASE_URL + FORCE_RULES comment | Matches usage mostly | Document that evening/insights ignore OPSPILOT_AI_* until B2 | **B2** |

**CLI role:** `cli.py` → `run_daily_ops` files-only — **VERIFIED** coherent with D-025.

---

## 3. Section C — AI layer (pre-B2)

### Call-site matrix (**VERIFIED**)

| Site | File:lines | Config | Prompt inputs | Parsing | Timeout/retry | FORCE_RULES |
|------|------------|--------|---------------|---------|---------------|-------------|
| Triage Claude | `claude_adapter.py:42–109` | `ANTHROPIC_API_KEY` only; model hardcoded `:71` | Full item: id, source, **subject, body, sender, tags** `:61–67` | JSON + enum validate; fence strip | None; except → rules | Via **factory only** |
| Conversation | `conversation_adapter.py:51–94` | **`ai_settings`** | System embeds triage **id/urgency/category/reason** (no bodies) `:27–32`; user = raw question `:84` | Text block | None | **No** |
| Evening | `evening_adapter.py:56–94` | `ANTHROPIC_API_KEY`; `MODEL` const | Same triage summary shape `:43–53` | Text | None | **No** |
| Insights | `insights_adapter.py:98–178` | `ANTHROPIC_API_KEY`; `MODEL` | id/urgency/category/**title**/reason `:69–75` | JSON + sanitize | None | **No** |
| Briefing | `briefing_adapter.py:11–115` | `ANTHROPIC_API_KEY`; model hardcoded | Counts + top-3 subjects + deadlines `:90–100` | Raw text | None; fallback string | **No** (pipeline) |
| Rules | `rule_based.py` | — | Local | — | — | Default under FORCE_RULES |

| ID | Sev | Evidence | Impact | Fix | Owner |
|----|-----|----------|--------|-----|-------|
| **C-01** | Critical | `factory.py:31–33` vs evening/insights/conversation ignoring FORCE_RULES | CI/tests with real key + socket hole → spend; docs claim FORCE_RULES “never constructs Anthropic” overstated | Gateway or shared `llm_allowed()`; all sites check FORCE_RULES / no-key | **B2** (hotfix **docs-only** warning now) |
| **C-02** | High | Split settings paths above | B2 migration harder; wrong model/env | All sites → `AISettings` then gateway | **B2** |
| **C-03** | High | `claude_adapter.py:65` body in prompt | X4 / free-tier train risk | Minimize: subject+tags+truncated body; or local-only triage | **B2** |
| **C-04** | High | No timeouts on `messages.create` | Hung workers | httpx timeout in gateway | **B2** |
| **C-05** | Medium | User question injection (`conversation` `:84`); item bodies in triage | Prompt injection | Gateway system/user separation; injection evals B3 | **B2**/**B3** |
| **C-06** | Medium | Pipeline always may call briefing adapter if key set (`run_daily_ops` path) | Unexpected spend on API POST /runs | FORCE_RULES / DEMO path skip AI briefing | **B2** |

### B2 migration map

| Call site | Task profile | Structured schema | Fallback | Test seam |
|-----------|--------------|-------------------|----------|-----------|
| `ClaudeAdapter.classify` | `triage.classify` | Triage JSON enums (existing) | RuleBasedAdapter | Fake provider + golden JSON |
| `answer_question` | `ask.converse` | Free text (later tools B5) | Polite no-key string | Fake complete() |
| `generate_evening_summary` | `evening.summary` | Free text → later structured | No-key / error string | Fake |
| `generate_insights` | `insights.patterns` | `{intro, insights[]}` | Empty insights + intro | Fake JSON |
| `generate_ai_briefing` | `briefing.daily` | Free text → later | Deterministic `briefing_generator` | Fake |

### Persistence B2 needs (from architecture / D-019) — **VERIFIED** targets

`LlmCall`: id, request_id, task, provider, model, latency_ms, ttft_ms, tokens_in/out, USD fields, prompt_version (sha256), status, error_code (`docs/architecture.md:208`, principal-review LlmCall row).

**Hooks:** wrap every gateway `complete`/`stream`/`complete_json` → persist row + OTel-compatible span (D-019) + Anthropic budget debit (D-023).

---

## 4. Section D — Test suite

| ID | Sev | Evidence | Impact | Fix | Owner |
|----|-----|----------|--------|-----|-------|
| **D-01** | High | No `tests/api` coverage of POST ask/evening/insights (**VERIFIED** grep); conversation unit mocks Anthropic | Regressions + spend risk | API tests with monkeypatched adapters / FORCE_RULES assertions | **B2** |
| **D-02** | Medium | Coverage floor 72; CI measured ~75% (`CHANGELOG` / PART 3 A3). Lowest live modules historically: evening/insights/claude adapters (prior CI table ~0–22% on some adapters) **INFERRED** from prior fix-pass TOTAL breakdown | Blind spots | Cover gateway seams; don’t chase legacy nlp % | **B2** |
| **D-03** | Medium | Strong: envelope, path traversal on runs, hermetic socket, alembic RT, import idempotency | Good core | Keep | — |
| **D-04** | Low | OpenAPI drift job (`ci.yml:95–101`) | Contract FE↔BE | Keep; add response schema tests for triage.subject_or_title | **B1.5** |
| **D-05** | Low | mypy `ignore_errors` on adapters/pipeline (`pyproject.toml:78–100`) | Type debt | Clear as B2 moves to `llm/` | **B2** |
| **D-06** | Low | Flake: randomly-seed = run_id (**VERIFIED**); time in briefing page is FE | Backend mostly deterministic | Freeze time in any new date tests | **B2** |

**Pyramid:** unit (nlp, cli, hermetic) + api TestClient + persistence + thin integration vertical slice — reasonable; missing adapter/API LLM seam tests.

---

## 5. Section E — CI/CD & supply chain

| ID | Sev | Evidence | Impact | Fix | Owner |
|----|-----|----------|--------|-----|-------|
| **E-01** | High | `actions/checkout@v4`, `setup-uv@v5`, `setup-node@v4` — tags not SHAs; **no** top-level `permissions:` (`ci.yml`) | Supply-chain / token scope | Pin SHAs; `permissions: contents: read` | **B1.5** or **docs-only chore** |
| **E-02** | Medium | No `pip-audit` / `uv export \| pip-audit` | Py vuln gap (npm audit exists `:134–136`) | Add free pip-audit job | **B1.5** / **B2** |
| **E-03** | Low | uv cache enabled (`:69–71`); npm cache on frontend job; backend OpenAPI uses `npx` without npm ci | Slightly slower/nondeterministic openapi-typescript | Pin openapi-typescript in package or uv tool | **B1.5** |
| **E-04** | Low | Jobs parallel: gitleaks \| backend \| frontend **VERIFIED** | OK | — | — |
| **E-05** | Medium | pre-commit: ruff+format+EOF+whitespace+gitleaks; CI: ruff+mypy+pytest+gitleaks — **no** pre-commit in CI; format `--check` not explicit in CI (ruff check only) | Drift | `ruff format --check` in CI; optional `pre-commit run` | **B1.5** |
| **E-06** | Low | Dependabot npm+uv+actions weekly (**VERIFIED**) | OK | — | — |
| **E-07** | Low | Windows local: Compose+uv documented | Reproducible **INFERRED** | Docker Playwright later for FE | **B1.5** |

---

## 6. Section F — Security

| ID | Sev | Evidence | Impact | Fix | Owner |
|----|-----|----------|--------|-----|-------|
| **F-01** | Medium | CORS allowlist localhost:5173 only (`app.py:11–28`); bind docs use 127.0.0.1 | Pre-B7 exposure low if not public | Keep; B7 tighten + CSP | **B7** |
| **F-02** | Medium | No rate limits (**VERIFIED** absent) | Risk only if publicly bound early | Do not expose before B7; add limits B7 | **B7** |
| **F-03** | Medium | `validation_handler` returns `exc.errors()` (`errors.py:19–26`) | Schema leakage | Sanitize details in prod | **B2**/**B7** |
| **F-04** | Low | Unhandled → generic 500 (`:48–55`); safe_error messages | Good | — | — |
| **F-05** | Low | Settings expose `api_key_set` bool only | Good | — | — |
| **F-06** | Medium | Importer `run_dir / filename` (`import_json.py:67–70`) — filename from metadata not path-sanitized | Local malicious history | Resolve + `relative_to(run_dir)` check | **B1.5** / **B2** |
| **F-07** | High | FORCE_RULES misuse / incomplete (see C-01) | Spend / false hermetic | B2 gateway | **B2** |
| **F-08** | Low | FE localStorage names only (prior UI audit); no CSP headers in API | B7 readiness gap | Security headers on public host | **B7** |
| **F-09** | Low | Pipeline logs `error_message` truncated 1000 (`pipeline.py:49`) | Possible PII in logs | Redact bodies | **B2** |

---

## 7. Section G — Data-model readiness B2–B6

**Current tables:** `work_items`, `runs`, `run_artifacts`, `triage_decisions` + `alembic_version` (**VERIFIED** `models.py`).

| Future | Fit now? | Notes |
|--------|----------|-------|
| **LlmCall (B2)** | Yes, additive | New table; FKs optional to `runs.run_id`; need UUID/bigserial convention |
| **Evals (B3)** | Yes | New tables; no conflict |
| **OAuth/Thread/Meeting/SyncCursor (B4)** | Yes | Need encrypted bytea column convention; SyncCursor natural keys |
| **Draft/Approval (B5)** | Yes | FK to work_items / runs |
| **Preference/Feedback (B6)** | Yes | Soft user key until auth |

| ID | Sev | Evidence | Impact | Fix | Owner |
|----|-----|----------|--------|-----|-------|
| **G-01** | High | String timestamps vs timestamptz `created_at` | Painful migrations later | ADR: all new ts = `timestamptz`; migrate strings opportunistically | **B2** (small ADR now) |
| **G-02** | Medium | PK mix: string business ids vs int surrogate on artifacts/triage | OK if documented | ADR: business `run_id`/`work_item_id` strings; internals serial/uuid | **B2** |
| **G-03** | Medium | JSONB used for tags/metadata (**VERIFIED**) | Good for flexible LlmCall extras | Prefer typed columns for metered fields | **B2** |
| **G-04** | Low | Cascade: artifacts CASCADE; triage SET NULL on run (**VERIFIED** `:58–76`) | Sensible | Keep pattern | — |

**Recommend lock NOW (small ADR, owner batch B2 start or docs-only):**  
1) `timestamptz` for all new time columns;  
2) `llm_calls` naming snake_plural;  
3) money/tokens as numeric/int, never float;  
4) `prompt_version` char(64) sha256;  
5) no secrets in JSONB;  
6) migrations operator-applied (D-011).

---

## 8. Section H — Batch readiness B2–B7

| Batch | Preconditions | Blockers | Missing ADR/decisions | Top risks | Zero-spend traps | Move? |
|-------|---------------|----------|----------------------|-----------|------------------|-------|
| **B1.5** | B1 merged **VERIFIED** | Docs stale; audits whitespace | B1.5 not in ROADMAP yet | Visual flake | None | Insert officially |
| **B2** | B1 done | Adapter sprawl; no LlmCall; FORCE_RULES incomplete | Gateway task profiles; prompt dir layout | Prepaid Anthropic footgun | Default must be Gemini/Groq/Ollama/rules; Anthropic gated D-023 | Don’t start until C-01/C-02 plan locked |
| **B3** | B2 gateway + fake providers | — | Eval dataset schema | Flaky LLM asserts | Evals must use fakes | After gateway |
| **B4** | Neon (**VERIFY**), OAuth Testing | Encrypted token design | D-016 exists; encryption ADR detail | Token leakage | No real inbox for visitors | Neon earlier only if B6 needs |
| **B5** | B2 stream + B4 mail | Ask UI dock (B1.5 helps) | DEMO_MODE send block | Accidental send | DEMO_MODE | After B4 |
| **B6** | Neon + encryption key in GHA; Telegram | Public BE forbidden (D-011 **VERIFIED**) | Runbook VERIFY 60-day GHA cron | Cron disabled on idle public repos | Secrets in GHA only | Feasible as designed |
| **B7** | Spine quality | Hosting free tiers | D-021 hosts | Quota surprises | **VERIFY AT DECISION TIME** Render/Neon/Pages | HMAC optional X2 |

**B6 feasibility:** D-011 in-runner cron + Neon + encrypted Google refresh in DB — **feasible** as ADR’d; no code yet.  
**B7 hosting:** D-021 — mark all free-tier claims **VERIFY AT DECISION TIME**.

---

## 9. Section I — Portfolio readiness

| What hiring reviewer sees | Gap | Own in |
|---------------------------|-----|--------|
| README hero still “B1 on branch…” | Looks unfinished after merge | **docs-only chore** |
| Strong ADR set D-001–D-025 | Architecture “pending merge” undercuts | **docs-only** |
| CI: gitleaks + tests + npm audit | No badge in README; Actions not SHA-pinned | **B1.5** |
| Honest CURRENT/TARGET dualism | Good signal | Keep |
| Hermetic story | Incomplete FORCE_RULES story if probed | **B2** |
| Highest leverage | (1) Docs merge status (2) B2 gateway+FORCE_RULES (3) CI permissions/pin/pip-audit (4) subject_or_title FE is UI batch | as listed |

---

## 10. Consolidated findings by owner batch

### B1.5-commit-1 chore
| ID | Sev | Summary |
|----|-----|---------|
| A-02 | Medium | Restore `docs/audits/*` from `ab5b5ee`; exclude audits/history from whitespace/EOF; `--markdown-linebreak-ext=md` |

### docs-only chore
| ID | Sev | Summary |
|----|-----|---------|
| A-01, A-03, A-08, I-01 | High/Med | Architecture/README/ROADMAP/PART3/master-record: B1 merged on main |
| A-04, A-05 | Low/Med | CHANGELOG polish; confirm Windows quick start |
| C-01 (doc warn) | — | Document FORCE_RULES triage-only until B2 |

### B1.5
| ID | Sev | Summary |
|----|-----|---------|
| E-01, E-02, E-03, E-05 | High/Med | CI permissions, SHA pins, pip-audit, format --check, pin openapi-typescript |
| B-04 | Medium | Clarify deprecated `api.main` |
| D-04 | Low | Contract assert subject_or_title |
| F-06 | Medium | Importer path containment (if not deferred to B2) |
| B-02 | High | Optional early `GET /runs?limit=` |

### B2
| ID | Sev | Summary |
|----|-----|---------|
| C-01–C-06, B-01 | Crit/High | Gateway; unify settings; FORCE_RULES all sites; X4; timeouts; services layer |
| B-02, B-03, B-06, G-01–G-03 | High/Med | Pagination; request_id; timestamptz ADR; LlmCall |
| D-01, D-02, D-05 | High/Med | Ask/evening/insights tests; mypy on llm/ |
| F-03, F-07, F-09 | Med/High | Error detail sanitize; FORCE_RULES; log redaction |
| H-01 | Medium | Execute migration map §C |

### B3
| ID | Sev | Summary |
|----|-----|---------|
| C-05 (evals) | Medium | Injection red-team on ask/triage |

### B4
| ID | Sev | Summary |
|----|-----|---------|
| B-08, H B4 | Med | Neon pool; OAuth encrypted storage |

### B5
| ID | Sev | Summary |
|----|-----|---------|
| H B5 | — | Draft/Approval + DEMO_MODE (schema ready) |

### B6
| ID | Sev | Summary |
|----|-----|---------|
| H B6 | — | Implement D-011; VERIFY GHA cron idle policy |

### B7
| ID | Sev | Summary |
|----|-----|---------|
| F-01, F-02, F-08, B-09 | Med | Public CORS, rate limits, CSP/headers, body limits |
| H B7 | — | VERIFY free-tier hosts at decision time |

---

## 11. After You Finish

### 1. Files changed
| Path | Change |
|------|--------|
| — | **None (Ask mode)** |

### 2. Command output summaries (read-only)
- HEAD `c5de149`, branch `main`, clean vs `origin/main`
- `docs/audits` vs `ab5b5ee`: equal insert/delete counts; **whitespace-only** (`git diff -w` empty)
- `docs/history`: **0** commits since `ab5b5ee`
- Grep/reads across ADRs, routes, adapters, persistence, CI, pre-commit, ROADMAP, PART 3, pyproject

### 3. Git
- **Branch:** `main`  
- **HEAD:** `c5de149a5a44e807c602c431a893919976f6d5fa`  
- **Status:** clean  

### 4. Push confirmation  
**N/A — read-only.**

### 5. Warnings / concerns
- Did not re-run pytest/CI or open every ADR body end-to-end (D-012/D-019/D-011/D-008/D-009/D-024/D-025 and indexes sampled).  
- Coverage “lowest modules” partially from prior B1 CI TOTAL table + static omission of adapter tests — not a fresh `coverage report` this session.  
- Did not execute README commands on Windows this session (A-05).  
- `uv.lock` skimmed via presence/CI `uv sync` only, not full audit.  
- Frontend security limited to cross-checks; full UI audit is separate.
