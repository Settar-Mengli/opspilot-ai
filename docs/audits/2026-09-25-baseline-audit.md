# OpsPilot AI — Baseline Audit (Read-Only)

**Audit date:** 2026-09-25
**Mode:** Ask / read-only (no file writes; no pytest/lint/build/npm-audit runs)
**Repo:** `c:\Dev\opspilot-ai` · remote claim: `Settar-Mengli/opspilot-ai` · branch `main`
**Preflight status:** The prompt says “OPERATOR PREFLIGHT OUTPUT (pasted below)” but **no preflight block was present**. Git/runtime facts below were gathered with **read-only** commands in this session. Anything that would have come only from a full preflight (pytest result, npm audit, lint/build) is tagged **UNVERIFIED-AT-RUNTIME**.

---

## 0. Executive summary

**Headline verdict:** OpsPilot is a credible **local demo** of a mobile-first AI chief-of-staff UX with a real Claude path and a deterministic rule-based fallback — but it is **not production-grade**, and its AI-engineering surface is still **thin and duplicated**. The strongest portfolio signal today is product/UX + a partial adapter seam; the weakest is LLM gateway maturity (retries, structured outputs, evals, observability, injection defenses) plus a **critical unauthenticated settings/key mutation API**.

**Top 10 findings (by severity)**

| # | ID | Severity | Title |
|---|-----|----------|--------|
| 1 | SEC-01 | CRITICAL | Unauthenticated `PATCH /api/settings` can set provider/model/**API key** for any client that can reach the API |
| 2 | AI-01 | HIGH | LLM client/model/key/prompt plumbing duplicated across 5 adapters; only conversation uses `AISettings` |
| 3 | AI-02 | HIGH | “OpenAI” is UI/settings theater — no OpenAI SDK, no client path; conversation rejects non-anthropic |
| 4 | AI-03 | HIGH | No timeouts/retries/rate-limit handling/streaming/telemetry on LLM calls |
| 5 | AI-04 | HIGH | No eval harness / golden sets / AI regression tests; LLM paths mostly untested |
| 6 | PROV-01 | HIGH | Docs/session records fragmented & stale; Session 1–3 not first-class repo records; CHANGELOG claims FE tests that do not exist |
| 7 | ARCH-01 | HIGH | `AISettings` process singleton + in-memory overrides → reset on restart, unsafe under multi-worker |
| 8 | BE-01 | MEDIUM | Unpinned Python deps (no lockfile); CI on 3.11 while local is 3.13 |
| 9 | FE-01 | MEDIUM | Gear still routes to `/connections`; panel lifecycle inconsistent; `index.css` ~2.3k lines |
| 10 | DEP-01 | HIGH | No containerization, no auth, file persistence, localhost CORS — not deployable publicly without redesign |

**Readiness rating by area (1–5)**

| Area | Rating | Note |
|------|--------|------|
| Ground truth / provenance | 2 | Session records partial; docs drift |
| Architecture | 3 | Clear modules; incomplete adapter migration |
| AI-engineering | 2 | Real Claude calls; weak gateway/evals/guards |
| Security & privacy | 1 | Settings key endpoint is a blocker |
| Backend quality | 3 | Solid early pipeline tests; AI gaps |
| Frontend quality | 3 | Polished demo UI; thin FE tests |
| CI/CD & DX | 2 | Basic CI only |
| Production readiness | 1 | Local demo only |
| Documentation | 2 | Many overlapping/stale docs |
| Portfolio AI signal | 2 | Complementary potential high; current depth low |

---

## 1. Ground truth & provenance

### 1a. Preflight / git ground truth

| Fact | Value | Tag |
|------|-------|-----|
| HEAD | `41a867828c61815b50579114ec127cb80b33c3ff` | VERIFIED |
| Short HEAD | `41a8678` | VERIFIED |
| Branch | `main` (tracks `origin/main`, up to date) | VERIFIED |
| Working tree | Clean (`nothing to commit`) | VERIFIED |
| Session 3 claimed HEAD | `41a8678` | **CONFIRMED** match |
| Local Python | `3.13.13` | VERIFIED |
| Local Node | `v24.14.0` | VERIFIED |
| `.env` on disk | Exists locally | VERIFIED |
| `.env` tracked | No (`git ls-files` only `.env.example`) | VERIFIED |
| `.env` ignored | Yes (`.gitignore:21`) | VERIFIED |

**Recent history (last 10):**

```
41a8678 fix: remove set-state-in-effect lint error in SettingsPage
5f19b77 docs: record session 3 progress and next steps
628bc17 feat: add frontend settings screen and model guard
e37370e feat: add env-configurable conversation provider seam
ae6af1a docs: record planning session - provider abstraction, conversation feature, monetization roadmap
55e5ba8 chore: remove orphaned components and unused CSS
7f0c35d style: tighten dashboard spacing to fit one mobile viewport
a58896f feat: replace dashboard ghost-links with three action buttons
7e48713 fix: remove stale mobile height override causing AskPanel top gap
1738b37 fix: panels use height 100 percent of fixed overlay to eliminate mobile gap
```

### 1b. Session claims verification table

**Important:** The prompt says Sessions 1–3 records were **attached**. They were **not present in the prompt body**. No files matching `*session*` exist in the repo. Session 2/3 content **is** embedded in `ROADMAP.md`. A discrete Session 1 record was **not found**. Claims below come from `ROADMAP.md`, other docs, and the audit prompt’s own stated context.

| Claim | Source | Verdict | Evidence |
|-------|--------|---------|----------|
| HEAD after Session 3 is `41a8678` | Session 3 / prompt | **CONFIRMED** | `git rev-parse` → `41a8678…` |
| Provider seam commit `e37370e` | ROADMAP Session 3 | **CONFIRMED** | In log; `settings.py` + conversation wiring exist |
| Frontend settings commit `628bc17` | ROADMAP Session 3 | **CONFIRMED** | In log; `SettingsPage.tsx` exists |
| `AISettings` singleton in `config/settings.py` | Session 3 | **CONFIRMED** | `ai_settings = AISettings()` at end of file |
| Conversation adapter uses settings | Session 3 | **CONFIRMED** | `from opspilot.config.settings import ai_settings` |
| `GET`/`PATCH /api/settings` | Session 3 | **CONFIRMED** | `main.py:204–230` |
| Key fallback `OPSPILOT_AI_API_KEY` → `ANTHROPIC_API_KEY` | Session 3 | **CONFIRMED** | `settings.py:32–41` |
| 51 tests passing | Session 3 | **CONFIRMED** count of test funcs = **51**; pass/fail **UNVERIFIED-AT-RUNTIME** (pytest not run) | AST count of `test_*` |
| Model-prefix guard (openai/`gpt-`, anthropic/`claude-`) | Session 3 | **CONFIRMED** | `main.py:183–196` |
| Settings overrides in-memory only | Session 3 open item | **CONFIRMED** | `override()` mutates instance fields only |
| 4 adapters not on settings | Session 3 open item | **CONFIRMED** | evening/insights/briefing/claude still `os.environ` / hardcoded model |
| Gear → `/connections` not `/settings` | Session 3 open item | **CONFIRMED** | `App.tsx:93` `NavLink to="/connections"` |
| Next session = migrate 4 adapters (Option B) | Session 3 | **CONFIRMED as decision text**; migration **not done** | ROADMAP:258–265 vs code |
| D-004 adapter seam | Session 2 | **CONFIRMED** | `docs/decisions.md:42–49` |
| Hardcoded model `claude-haiku-4-5-20251001` in 5 places | Session 2 | **PARTIALLY SUPERSEDED** — conversation uses settings default; 4 adapters still hardcode | see §2c |
| BYOK ruled out (monetization) | Session 2 | **CONFIRMED as recorded decision**; **product contradiction** with settings key UI | ROADMAP:192–194 vs `SettingsPage` |
| `/ask` = `{question, assistant_name}` → `{answer}` | Session 2 | **CONFIRMED** | `AskRequest` / `ask()` |
| Multi-turn history planned client-side | Session 2 | **CONFIRMED as plan**; **not implemented** | AskPanel sends single question only |
| `TriageRecord` lacks title/subject | Session 2 | **CONFIRMED** | `schemas.py:39–46` |
| AllItemsPage shows `id` as title | Session 2 | **CONFIRMED** | `AllItemsPage.tsx:87` `{r.id}` |
| WeekPanel static data | Session 2 | **CONFIRMED** | `WeekPanel.tsx:15–21` |
| `dayShapeLine` static placeholder | Session 2 | **CONFIRMED** | `DashboardPage.tsx:55` |
| Nine `opspilot_*_mobile.html` files | Session 2 | **CONFIRMED absent** | glob 0; design refs are numbered HTML instead |
| Panel lifecycle mixed (conditional vs class) | Session 2 | **CONFIRMED** | Ask/Evening conditional; Notify class; Priorities early-return |
| H-1: non-localhost API URLs rejected | Prompt / Session 1 context | **CONFIRMED** | `client.ts:27–29` |
| Approved fictional companies list | Session 1 / design README | **CONFIRMED** | `frontend/design-reference/README.md:73` |
| Frontend Vitest tests exist | CHANGELOG / PROGRESS | **REFUTED** | `frontend/src/**/*.{test,spec}.*` → 0 files |
| PROGRESS “42 passed” restart handoff | PROGRESS.md | **STALE** vs current 51 test funcs | PROGRESS:104 |
| `docs/ARCHITECTURE.md` path in README | README:91 | **REFUTED** (actual `docs/architecture.md`) | case/name mismatch |
| Models are Pydantic | architecture.md:87 | **REFUTED** | dataclasses in `schemas.py` |
| Components make no API calls | architecture.md:67 | **REFUTED** | AskPanel/Evening/Insights call API |

### 1c. Documentation inventory

| Doc | Purpose | Staleness / contradictions | Overlap |
|-----|---------|----------------------------|---------|
| `README.md` | Recruiter/demo entry, setup | Partially current (settings env vars); cites wrong architecture filename; Windows activate example only | Overlaps ROADMAP phases |
| `ROADMAP.md` | Phases A–E + Session 2/3 planning | Most current session record; Phase D BYOK vs Session 2 “BYOK ruled out” vs Settings key UI — **three-way tension** | Overlaps README phases |
| `CHANGELOG.md` | Keep-a-Changelog | Stale: claims FE tests; missing Session 3 settings feature | Overlaps PROGRESS |
| `PROGRESS.md` | Append-only step log | Stops at early “Safe Sprint”; **does not include** Sessions 1–3 mobile/AI work | Overlaps CHANGELOG |
| `AGENTS.md` | Agent operating rules | Still: local-only, no paid API, no real integrations — **conflicts with production goal + Anthropic usage** | Unique as agent rules |
| `CONTRIBUTING.md` | Branch/commit PR norms | Fine; thin | Unique |
| `docs/decisions.md` | ADR-lite (D-001…D-007) | D-004 present; **no decisions for settings/BYOK/Session 2–3** | Should be SoT for decisions |
| `docs/architecture.md` | Architecture narrative | Stale routes (3), wrong schema claim, incomplete endpoint list, false “no API in components” | Overlaps README |
| `docs/milestones.md` | Early milestone plan | Pre-UI/LLM era | Overlaps ROADMAP |
| `docs/demo.md` | Demo walkthrough | Not fully re-read end-to-end this audit; treat as possibly stale | Overlaps README |
| `docs/glossary.md` | Terms | Not fully re-read | Unique |
| `docs/scheduling.md` | Scheduling design (not implemented) | Likely still accurate that scheduling is not implemented | Unique |
| `docs/copilot-workflow.md` | Copilot process | Overlaps AGENTS | Overlaps AGENTS |
| `docs/ai-memory/README.md` | Memory notes | Scaffold | Unique |
| `frontend/README.md` | FE-specific | Not fully re-read | Overlaps root README |
| `frontend/design-reference/*` | Visual targets + company list | 10 numbered HTML files; **not** `opspilot_*_mobile.html` | Design SoT |

**D-004 location:** `docs/decisions.md` lines 42–49 — “Adapter Seam For Future Models” — **VERIFIED**.

### 1d. Session records & mobile HTML references

- Session records **in repo as standalone files:** **No**.
- Session 2/3 narrative: **in `ROADMAP.md`** only.
- `opspilot_*_mobile.html`: **0 matches anywhere**.
- Present instead: `frontend/design-reference/01-…` through `10-….html` (10 files).

### 1e. Secret hygiene

| Check | Result | Tag |
|-------|--------|-----|
| Real key ever committed? | History search for `sk-ant-` / long `sk-` patterns did not surface committed secret blobs; hits were docs mentioning `ANTHROPIC_API_KEY` loading | VERIFIED (search performed); residual risk if exotic formats used |
| `.env` ignored & untracked | Yes | VERIFIED |
| Keys in examples/tests/docs | `.env.example` uses placeholders; tests use `"legacy-key"` / `"primary-key"` fakes | VERIFIED |
| Local `.env` exists | Yes (operator machine) — **not** in git | VERIFIED |

---

## 2. Architecture map

### 2a. Module map

**Backend `src/opspilot/`**

| Module | Responsibility | Entry / consumers |
|--------|----------------|-------------------|
| `api/main.py` | HTTP surface, CORS, settings | uvicorn |
| `cli.py` | CLI `run` | subprocess from `/run`, human |
| `pipeline/run_daily_ops.py` | Orchestrate ingest→triage→actions→briefing→history | CLI |
| `adapters/*` | AI + rule triage / generative features | pipeline, API |
| `config/settings.py` | Runtime AI settings singleton | conversation + API settings |
| `models/schemas.py` | Dataclass schemas + validation | ingest/rules/nlp |
| `ingest/` | Load + normalize JSON | pipeline |
| `rules/` | Keyword triage | rule adapter |
| `nlp/` | Actions, rule briefing, drafts | pipeline |
| `history/` | Immutable run artifacts | pipeline + API |
| `utils/` | file_io, logging | many |
| `capabilities/` | Static integration catalog | `/capabilities` |

**Dependency direction (intended):** API → adapters/history; CLI → pipeline → adapters/ingest/nlp/rules → models/utils.
**Issues found:**

- **Dead import:** `classify_work_item` imported in `run_daily_ops.py:26` but unused (adapter used instead) — MEDIUM dead code.
- **Adapter bypass of D-004 “seam”:** generative adapters are free functions, not `TriageAdapter`; factory only covers triage classify.
- **No circular imports observed** in the import list reviewed — VERIFIED for scanned imports; full graph not formally cycle-checked.

**Frontend `frontend/src/`**

| Area | Responsibility |
|------|----------------|
| `App.tsx` | Shell, routes, panel orchestration, health |
| `pages/*` | Dashboard, items, insights, briefing, connections, settings |
| `components/*` | Panels, dock, onboarding, skeletons |
| `api/client.ts` | Fetch client + localhost sanitize |
| `hooks/*` | Names in localStorage, speech, shortcut |
| `index.css` | Entire design system (~2374 lines / ~58KB) |

### 2b. Endpoint inventory

| Method | Path | Request | Response | Validation | Error shape | Sync | LLM? |
|--------|------|---------|----------|------------|-------------|------|------|
| GET | `/health` | — | `"ok"` text | — | N/A | sync | no |
| GET | `/api/settings` | — | provider/model/key flags | — | N/A | sync | no |
| PATCH | `/api/settings` | `SettingsPatchRequest` | same | model prefix guard; **no provider allowlist** | `_safe_error` or raw | sync | no |
| POST | `/run` | `input_file`, `date` | `{status, stdout}` | date, path traversal | mix: 400 string / `_safe_error` | sync subprocess | maybe (pipeline) |
| GET | `/briefing` | — | text | file exists | 404 string detail | sync | no |
| GET | `/triage` | — | JSON array | file exists | 404 string | sync | no |
| GET | `/ai-briefing` | — | text | fallback to daily | 404 string | sync | no (reads file) |
| GET | `/runs` | — | metadata list | sanitized | — | sync | no |
| GET | `/runs/{run_id}` | — | metadata | sanitize | mix | sync | no |
| GET | `/runs/{id}/triage` | — | JSON | — | `_safe_error` / 404 | sync | no |
| GET | `/runs/{id}/briefing` | — | text | — | mix | sync | no |
| GET | `/runs/{id}/ai-briefing` | — | text | fallback | mix | sync | no |
| POST | `/ask` | question, assistant_name | `{answer}` | Field length + name pattern | Pydantic 422; LLM errors soft-string | sync | **yes** |
| POST | `/evening-summary` | assistant_name | `{summary}` | name pattern | soft-string | sync | **yes** |
| POST | `/insights` | assistant_name | `{intro, insights}` | name pattern | soft fallback dict | sync | **yes** |
| GET | `/inputs` | — | `{files}` | — | — | sync | no |
| GET | `/capabilities` | — | list | — | — | sync | no |
| GET | `/capabilities/{id}` | — | one | — | 404 string | sync | no |

**Flags:**

- **Inconsistent prefixes:** `/api/settings` vs bare `/ask`, `/triage`, etc. — VERIFIED.
- **No API versioning** (`/v1`) — VERIFIED.
- **Inconsistent errors:** some `detail: str`, some `detail: {error, message}` — VERIFIED in `main.py`.
- All handlers are **def** (sync), including LLM calls — blocks event loop under load — VERIFIED.

### 2c. Adapter pattern

**What the abstraction actually is**

- `TriageAdapter` ABC with `classify(WorkItem) -> TriageRecord` (`base.py:12–17`).
- `factory.get_adapter()` tries `ClaudeAdapter()`, else `RuleBasedAdapter()` (`factory.py:12–24`).
- Generative features (`conversation`, `evening`, `insights`, `briefing`) are **not** behind that ABC — parallel free-function adapters.

**Where bypassed**

- Conversation/evening/insights/briefing never go through factory.
- Claude path constructs Anthropic client inside each module.
- Settings seam only wired into conversation.

**Duplicated LLM plumbing (exact)**

| Concern | conversation | evening | insights | briefing | claude |
|---------|--------------|---------|----------|----------|--------|
| Client ctor | `Anthropic(api_key=…)` | same | same | `anthropic.Anthropic` | same |
| Model string | `ai_settings.model` | hardcoded `MODEL` | hardcoded `MODEL` | hardcoded | hardcoded |
| Key read | `ai_settings.api_key` | `ANTHROPIC_API_KEY` only | same | same | same at init |
| Parse | text block | text block | JSON + fence strip | raw text | JSON + fence strip |
| Retries | none | none | none | none | none |
| Timeouts | none | none | none | none | none |

### 2d. `config/settings.py`

```75:75:src/opspilot/config/settings.py
ai_settings = AISettings()
```

| Topic | Assessment | Tag |
|-------|------------|-----|
| Singleton | Module-level `ai_settings` | VERIFIED |
| Runtime mutation | `override()` via PATCH | VERIFIED |
| Thread safety | No lock; concurrent PATCH races possible | INFERRED |
| Multi-worker | Each process has own copy; PATCH not shared | INFERRED (standard Python) |
| Restart loss | Overrides discarded | VERIFIED |
| Import-time side effects | Resolves env at import; `load_dotenv()` in `main.py:14` and again in pipeline | VERIFIED |
| load_dotenv placement | After some imports in main? Actually before adapter imports — OK for API; CLI/pipeline also load | VERIFIED |

### 2e. Data layer

| Topic | Finding | Tag |
|-------|---------|-----|
| Concurrency | Non-atomic `open("w")` writes (`file_io.py:15–18`) — crash can truncate | VERIFIED |
| Schema validation | Raw input validated; triage output is free-form dicts from adapters | VERIFIED |
| Path handling | `/run` restricts to `data/raw` filenames; run_id regex in history | VERIFIED (partial read of history) |
| `TriageRecord` title | **No title/subject field** — only id + labels + reasons | VERIFIED `schemas.py:39–46` |
| Impact on AI quality | Conversation/evening prompts get id/urgency/category/reason — **not subject/body**. Insights looks for `subject_or_title` on triage dicts (usually absent). Briefing adapter uses `item.subject` / `item.title` — **WorkItem has `subject_or_title`**, so top-3 subjects often empty | VERIFIED |
| Sample data | Fictional companies present in `sample_input.json` | VERIFIED |

### 2f. State map

| Location | What | Deploy implication |
|----------|------|--------------------|
| Server memory | `ai_settings` overrides | Lost on restart; not multi-instance safe |
| Files | `data/output/*`, `data/history/runs/*`, `data/raw/*` | Need durable volume; history gitignored |
| localStorage | user name, assistant name | Device-local; no server identity |
| Browser UI state | panels, messages (Ask thread in React state only) | Lost on refresh |

---

## 3. AI-engineering layer

### 3a. Prompt inventory

| Prompt | Location | Construction | Versioned? | User/data ingress |
|--------|----------|--------------|------------|-------------------|
| Conversation system | `conversation_adapter.py:34–47` | f-string with `assistant_name` + triage lines | No | `assistant_name`; triage fields; **user question is user message** |
| Conversation user | same `:86` | raw `question.strip()` | No | direct user input |
| Evening system | `evening_adapter.py:24–40` | f-string `assistant_name` | No | name only |
| Evening user | `:74` | formatted triage lines | No | triage content (indirect) |
| Insights system | `insights_adapter.py:27–62` | f-string | No | name |
| Insights user | `:116` | triage lines + attempted title | No | triage (indirect) |
| Briefing system | `briefing_adapter.py:65–71` | string literal | No | — |
| Briefing user | `:73–83` | f-string counts + top items | No | triage/actions (indirect) |
| Claude triage system | `claude_adapter.py:16–33` | constant | No | — |
| Claude triage user | `:62–69` | f-string full WorkItem incl. body | No | **full item body** (indirect injection surface) |

Duplication: voice/tone blocks repeated across conversation/evening/insights.

### 3b. Prompt injection

| Vector | Status | Evidence |
|--------|--------|----------|
| Direct via `question` | Validated length 1–2000; **no injection filtering**; enters as user message | `AskRequest`; conversation adapter |
| Direct via `assistant_name` | Pattern `^[A-Za-z0-9 .'\-]+$` max 60 — mitigates some injection into system prompt | `main.py:81–86` |
| Indirect via triage text | Reasons/bodies flow into prompts; **no sanitization** | conversation/evening/insights/claude |
| Validation on LLM-bound fields | Strong on assistant_name; weak on question content; none on triage | VERIFIED |
| XSS on render | **No `dangerouslySetInnerHTML`**; React text nodes for Ask/Insights | VERIFIED — XSS risk low for HTML injection; markdown not rendered |

### 3c. Output handling

| Output | Parsing | Robustness | Native structured output / tools? |
|--------|---------|------------|-----------------------------------|
| Insights JSON | `json.loads` + fence strip + soft field sanitize | Fallback dict on failure | **No** |
| Claude triage JSON | fence strip + `json.loads` + enum checks; else rule fallback | Better than insights | **No** |
| `[[DRAFT]]` markers | **Not implemented** in code (planned Session 2 Phase B) | N/A | No |
| Briefing markdown | returned as plain text; FE strips headings (commit history) | Ad hoc | No |

### 3d. Reliability

| Concern | Status |
|---------|--------|
| LLM timeouts | **None** |
| Retries/backoff | **None** |
| Rate-limit handling | **None** |
| HTTP mapping of LLM errors | Soft string/fallback in body; often still **200** | VERIFIED |
| Partial failure | Per-item Claude→rules fallback in triage; generative soft fail | VERIFIED |
| Streaming | **None** |

Pipeline `/run` has 120s subprocess timeout — VERIFIED; LLM calls inside pipeline do not.

### 3e. Provider abstraction

- **OpenAI end-to-end?** **No.** Settings UI offers `openai`; PATCH may set provider; conversation returns unavailable if not anthropic; **no `openai` package** in `pyproject.toml`. Test explicitly sets openai and expects failure message — VERIFIED `test_conversation_adapter.py:108–117`.
- **Model-prefix guard:** rejects openai models not starting with `gpt-` — **incorrect for** `o1`, `o3`, `chatgpt-…`, etc. (verify at decision time). Unknown providers skip both checks — VERIFIED `main.py:183–196`.
- **Four unmigrated adapters hardcode:** `ANTHROPIC_API_KEY` env read; model `claude-haiku-4-5-20251001`; direct `Anthropic` client; ignore `OPSPILOT_AI_*` and runtime PATCH overrides — VERIFIED.

### 3f. Observability & cost

Logged: exception messages / warnings on failure.
**Missing:** tokens, latency, cost, request IDs, tracing, prompt/version IDs — VERIFIED by grep (only `max_tokens` params, no usage logging).

### 3g. Evaluation

| Question | Answer |
|----------|--------|
| Evals / golden sets / AI regression? | **None found** |
| LLM tests | Conversation: **mocked** Anthropic client; no evening/insights/claude/briefing adapter tests |
| `rule_based` as deterministic baseline? | **Yes, usable** for triage classify determinism; not wired as eval harness |

### 3h. Grounding

- Prompt instructs: answer from triage; don’t invent; cite item IDs — VERIFIED.
- Context **omits titles/bodies** for Ask — increases hallucination / vague answers — VERIFIED.
- No citation enforcement or retrieval grounding beyond prompt text — VERIFIED.

### 3i. Conversation vs planned multi-turn

| Aspect | Current | Planned (Session 2) |
|--------|---------|---------------------|
| Contract | single question | optional history |
| FE | thread UI, but each send is independent | send bounded history |
| Token growth | low today; **will grow** if naïve history append without caps | Session 2 mentions caps — not built |

### 3j. Caching / routing opportunities

- **Prompt caching:** Anthropic cacheable system prefixes possible once prompts stabilized — recommend later.
- **Response caching:** cache insights/evening for identical triage hash — cheap win.
- **Per-task routing:** triage (cheap/deterministic) vs conversation (stronger) vs insights (JSON) — fits free-tier constraint.

---

## 4. Security & privacy

### SEC-01 — `PATCH /api/settings` (CRITICAL)

```210:230:src/opspilot/api/main.py
@app.patch("/api/settings", response_class=JSONResponse)
def patch_settings(payload: SettingsPatchRequest) -> dict[str, object]:
    """Update runtime AI settings without restarting the API."""
    ...
    ai_settings.override(
        provider=payload.provider,
        model=payload.model,
        api_key=payload.api_key,
    )
```

- **No authentication.**
- Any origin allowed by CORS (`localhost:5173` / `127.0.0.1:5173`) can set a key.
- If API is ever bound to `0.0.0.0` or exposed publicly, **any client can inject keys / swap providers**.
- Key masking on GET is present (`sk-••••` + last 4) — VERIFIED; full key still held in memory.

### Other security

| Topic | Finding | Sev |
|-------|---------|-----|
| CORS | Local UI only; methods include PATCH | MEDIUM (ok local; blocks real domains) |
| Host binding | README uses default uvicorn (typically localhost) — good for local | LOW locally |
| Validation coverage | Strong on `/run` paths & assistant_name; weak on settings provider enum | HIGH |
| Secrets in logs/errors | Pipeline logs stderr snippet; LLM exceptions logged — risk if SDK echoes secrets | MEDIUM INFERRED |
| Dep vulns | npm audit **not run** | UNVERIFIED-AT-RUNTIME |
| Python pinning | Unpinned `fastapi`, `uvicorn`, `anthropic>=0.25` — supply-chain drift | HIGH |
| localStorage | Names only — low sensitivity | LOW |
| BYOK contradiction | Session 2 ruled out BYOK; Session 3 shipped browser API-key form that PATCHes server memory — **effective BYOK without threat model** | CRITICAL product/security |

---

## 5. Backend quality

| Topic | Finding |
|-------|---------|
| Typing | Present in many modules; **no mypy/pyright/ruff config found** |
| Lint/format | No Python lint gate in CI |
| Lockfile | **No** `uv.lock` / `poetry.lock` / `requirements.txt`; FE has `package-lock.json` |
| Logging | Structured helpers exist; LLM path inconsistent |
| Dead code | Unused `classify_work_item` import in pipeline |
| Tests | **51** functions: api 25, briefing 7, conversation 5, loader 4, integration 4, classifier 3, action 2, cli 1 |
| Coverage gaps | No tests for `/ask`, `/insights`, `/evening-summary`, `/api/settings`, capabilities, AI adapters except conversation |
| Mocking | Conversation stubs Anthropic; API mocks subprocess for timeout/failure |

---

## 6. Frontend quality

| Topic | Finding |
|-------|---------|
| TS strictness | `tsconfig.app.json` has unused checks but **no `"strict": true`** visible |
| `any` | No TypeScript `any` hits in `frontend/src` (only English word “any”) |
| API client H-1 | Non-localhost rejected — VERIFIED |
| Timeouts | **No fetch AbortSignal/timeouts** |
| Error handling | Mixed (`toApiError` vs bare `Ask failed: status`) |
| Gear routing | Still `/connections` — VERIFIED |
| Panel lifecycle | Ask/Evening: mount/unmount; Notify/Voice: CSS `open`; Priorities/Week: `if (!open) return null` |
| `index.css` | ~2374 lines / ~58KB — monolithic |
| a11y | Many `aria-label`s; `prefers-reduced-motion` gated animations; incomplete focus/contrast audit (not visually measured) |
| FE tests | **None in `frontend/src`** despite CHANGELOG claims |
| Build | `tsc -b && vite build` in package.json; **build not run this audit** |

---

## 7. CI/CD & developer experience

**`.github/workflows/ci.yml` gates:**

1. Backend: Python **3.11**, `pip install -e .[dev]`, `pytest -q`
2. Frontend: Node 20, `npm ci`, `npm run lint`, `npm run build`

**Missing:** typecheck-only job (build embeds `tsc`), coverage, security/secret scan, Dependabot/Renovate, Python lint, Python version matrix matching 3.13, pre-commit hooks (**none**).

**README setup:** Windows venv activate shown; Unix not; Python “3.10+” vs local 3.13 vs CI 3.11 — workable but imprecise.

---

## 8. Production & deployment readiness

**Present:** local FastAPI + Vite; file persistence; soft LLM fallbacks; `/health` liveness only.

**Absent:** Dockerfile/compose, readiness/startup probes, structured JSON logs, HTTPS, auth, durable multi-user storage, CORS for real domains, graceful multi-worker settings, secret manager.

**Blockers to public free hosting (unordered):**

1. Unauthenticated settings/key mutation (SEC-01)
2. No auth / multi-tenant isolation
3. File-based shared state + gitignored history
4. CORS localhost-only
5. Sync LLM on request thread
6. Paid Anthropic dependency vs “free-only” product constraint (needs free-tier or local model strategy)
7. No container/procfile story
8. AGENTS.md local-only rule vs deploy goal

**Free-compatible host candidates (tradeoffs; not a pick):**

| Candidate | Tradeoff |
|-----------|----------|
| Render free web | Sleeps; good for demo; needs Docker/native Python |
| Fly.io free allowance | More ops; verify quotas at decision time |
| Railway trial/free | Limits change often — verify |
| Cloudflare Pages (FE) + separate API | FE easy; API still needed elsewhere |
| Vercel (FE only) | Matches ROADMAP Phase B FE; API elsewhere |
| Self-host VPS free tier / home lab | Full control; not “zero ops” |

---

## 9. Documentation & record-keeping architecture

### Proposed SoT map (one concern → one file)

| Concern | Proposed SoT | Action for existing docs |
|---------|--------------|--------------------------|
| Permanent session record | `RECORD.md` (append-only PART blocks) | **Create**; absorb Session 1–3 + this audit |
| Status / what’s true now | `PROGRESS.md` → slim “Current State” pointer into RECORD | **Keep** as pointer OR merge into RECORD and retire body |
| Roadmap / phases | `ROADMAP.md` | **Keep**; remove narrative session dumps once in RECORD |
| Decisions | `docs/decisions.md` | **Keep**; add D-00x for settings/BYOK/production |
| Changelog (releases) | `CHANGELOG.md` | **Keep**; stop duplicating session notes |
| Agent rules | `AGENTS.md` | **Keep**; revise scope constraints when owner decides |
| Architecture | `docs/architecture.md` | **Keep**; rewrite to match code; fix README link |
| Contributing | `CONTRIBUTING.md` | **Keep** |
| Design visual SoT | `frontend/design-reference/` | **Keep** |
| Early milestones | `docs/milestones.md` | **Retire or archive** into RECORD PART 0 — superseded by ROADMAP |
| demo/glossary/scheduling/copilot/ai-memory | keep if accurate | **Merge overlaps** into architecture/RECORD; avoid parallel “truth” |

### Proposed filename

**`RECORD.md`** at repo root (matches owner’s other-repo convention).

### OUTLINE ONLY — PART 0 (Sessions 1–3 history)

1. Provenance note: sources of claims (chat exports / ROADMAP embeds); verification status.
2. Session 1: redesign goals, H-1 API sanitize, fictional company list, mobile reference naming confusion.
3. Session 2: D-004 extension plan, conversation multi-turn plan, monetization/BYOK ruling, backlog (TriageRecord title, panels).
4. Session 3: settings seam commits, open items, Option B decision.
5. Claim ledger: CONFIRMED/REFUTED table (from this audit §1b).

### OUTLINE ONLY — PART 1 (this audit baseline)

1. Executive verdict + readiness ratings.
2. Architecture & endpoint snapshot at HEAD `41a8678`.
3. AI layer inventory (prompts, gaps).
4. Security findings (SEC-01 et al.).
5. Quality/CI/deploy blockers.
6. Portfolio gap + candidate table.
7. Draft milestone sequence M0… (discussion only).
8. Open decisions for owner.

---

## 10. Portfolio & AI-engineering gap analysis

**What it demonstrates today (hiring-manager lens):**

- End-to-end product slice: ingest → triage → briefing → React mobile UI.
- Adapter *idea* for triage + rule fallback.
- Some API hardening (path traversal, CORS allowlist, metadata sanitization).
- Light provider config seam (incomplete).

**What is missing for AI Engineer roles (complementary to LangGraph/RAG/Celery/MCP/JWT portfolio):**

- Unified LLM gateway, structured outputs/tool use, eval harness, injection tests, observability, streaming agent, multi-provider free-tier reality — i.e. **production LLM systems engineering**.

### Candidate table

| Candidate | Demonstrates | Existing seam | Prereqs | Effort | Risk | Free-tier | Overlap w/ other repo | Verdict |
|-----------|--------------|---------------|---------|--------|------|-----------|----------------------|---------|
| Single LLM gateway module | Production LLM ops | adapters/* | SEC decision on keys | L | Med | Yes (code) | Partial (patterns) | **DO** |
| Versioned prompt templates + tests | Prompt eng discipline | adapter prompts | gateway helpful | M | Low | Yes | None | **DO** |
| Offline eval harness on sample data | Eval systems | `rule_based`, fixtures | golden JSON | L | Med | Yes (judge may cost — use free/local) | Partial | **DO** |
| Native structured outputs / tools | Modern LLM APIs | insights/claude JSON hacks | Anthropic tools or JSON mode | M–L | Med | Verify pricing | Partial | **DO** |
| Tool-using conversational agent + SSE | Agents + streaming | `/ask`, AskPanel | multi-turn contract | XL | High | Verify | **Full** if LangGraph clone — keep **simpler** than other repo | **DO** (lighter than other repo) |
| LLM observability (tokens/latency/cost) | Ops excellence | logger | gateway | M | Low | Self-host OpenTelemetry / log JSON | Partial | **DO** |
| Injection guardrails + adversarial tests | Safety eng | AskRequest / triage ingress | eval harness | M–L | Med | Yes | None | **DO** |
| Real multi-provider (free APIs / local) | Cost/constraint eng | settings provider field | gateway; drop gpt- prefix myth | L | Med | Verify free tiers (Groq/Gemini/Ollama) | Partial | **DO** |
| SQLite + minimal auth | Deployability | file_io / settings | threat model | L–XL | Med | Yes | Partial (other has Alembic/JWT — keep minimal) | **DO** when deploying |
| Composio / direct integration | Integration eng | `capabilities/registry.py` | OAuth secrets; may need paid | XL | High | Flag account/cost | None–Partial | **LATER** (Phase B product) |
| LangGraph multi-agent clone | Orchestration | — | — | XL | High | — | **Full** | **SKIP** (duplicate portfolio) |
| Qdrant RAG clone | Retrieval | weak need (tiny triage set) | — | L | Med | — | **Full** | **SKIP** until corpus justifies |
| Celery workers | Async jobs | `/run` subprocess | — | L | Med | — | **Full** | **LATER**/SKIP early |
| MCP server | Tool protocol | capabilities | — | L | Med | — | **Full** | **SKIP** early (Phase D BYOA already in ROADMAP) |

---

## 11. Recommended sequence (draft for discussion)

### M0 — Records & docs foundation
- **Goal:** Cold-resume SoT; stop drift.
- **Scope:** `RECORD.md` PART 0+1; fix README architecture link; add decisions for settings/BYOK; trim ROADMAP session dumps into RECORD; reconcile AGENTS constraints with production intent (decision).
- **Exit:** PART 0/1 merged; owner agrees SoT map; no contradictory “current state” paragraphs.
- **Deps:** none.

### M1 — Security & settings architecture (blocks everything public)
- **Goal:** Remove SEC-01 class exposure; clarify key model.
- **Scope:** Disable or auth-protect PATCH key; server-env-only keys **or** explicit BYOK with threat model; provider allowlist; persist settings safely if needed.
- **Exit:** Tests prove unauthenticated key set fails; threat model decision recorded as D-00x.
- **Deps:** M0 decision list.

### M2 — LLM gateway + migrate 4 adapters
- **Goal:** One client path: retries, timeouts, errors, telemetry hooks.
- **Scope:** New module; migrate evening/insights/briefing/claude; fix OpenAI theater or implement for real; correct model validation.
- **Exit:** All adapters call gateway; unit tests with fakes; conversation+insights smoke.
- **Deps:** M1 key policy.

### M3 — Data shape uplift for AI quality
- **Goal:** Triage/context includes titles/subjects; FE shows titles.
- **Scope:** Extend `TriageRecord` or join WorkItem; fix briefing_adapter subject bug; update prompts.
- **Exit:** Ask/insights reference real subjects; AllItemsPage shows titles; tests.
- **Deps:** none hard (can parallel after M0).

### M4 — Prompts, structured outputs, guardrails
- **Goal:** Versioned prompts; JSON/schema outputs; injection tests.
- **Exit:** Prompt snapshot tests; adversarial suite green; insights/claude use schema validation shared helper.
- **Deps:** M2.

### M5 — Eval harness in CI
- **Goal:** Deterministic checks + optional free/local judge; rule_based baseline.
- **Exit:** CI job on sample_input; no paid key required for default lane.
- **Deps:** M3–M4 helpful.

### M6 — Conversation Phase A + streaming (portfolio AI core)
- **Goal:** Multi-turn with caps; SSE token stream; tool-read triage by id.
- **Exit:** Live smoke; FE consumes stream; token-cap tests.
- **Deps:** M2, M4.

### M7 — Persistence + minimal auth + deploy spike
- **Goal:** SQLite + minimal auth; CORS for chosen free host; health/ready.
- **Exit:** Deployed demo URL with fictional data only; secrets via host env.
- **Deps:** M1; product Phase B decision.

---

## 12. Decisions required from the owner

| Decision | Options | Tradeoffs | Recommendation | Blocks |
|----------|---------|-----------|----------------|--------|
| Server-held key vs BYOK | A) Env-only server key, remove key from PATCH/UI **B)** Explicit BYOK with auth **C)** Hybrid | A safest for demo; B matches Settings UI but needs auth; C complex | **A for now** (aligns Session 2 monetization + free-only); revisit BYOK at Phase D | M1, deploy |
| Long-term LLM under free-only | Anthropic free/trial credits; Gemini/Groq free; Ollama local for eval | Credits expire; local weaker UX | **Hosted free-tier for demo + Ollama for CI evals** (verify quotas at decision time) | M2, M5 |
| Do AGENTS.md local-only rules still apply? | Keep / revise / split “demo vs prod” | Keeping blocks Phase B honesty | **Revise**: allow free-tier APIs + fictional data; still no paid SaaS | M0, roadmap honesty |
| Public vs private repo | Public portfolio / private until hardened | Public + SEC-01 is dangerous if API ever exposed | **Private until M1**; then public | portfolio timing |
| Persistence | Stay JSON / SQLite / Postgres | JSON fine local; SQLite enough for first deploy | **SQLite first** when deploying | M7 |
| Auth scope | None / shared password / Google OAuth | OAuth = product Phase B | **None until deploy spike; then minimal** (not full JWT stack unless needed) | M7 |
| OpenAI in UI | Remove until real / implement | Theater harms credibility | **Remove or implement** — no fake option | M2 |
| Gear → settings vs connections | Point gear to `/settings` / keep connections | UX debt | **Gear → `/settings`**; connections via nav | FE polish |
| Composio timing | Now / Phase B | Account + cost | **LATER** | integration epic |
| Duplicate other-repo stack | LangGraph/RAG/Celery/MCP now? | Portfolio cannibalization | **SKIP** those; do gateway/evals/streaming/guardrails | roadmap |

---

## 13. Consolidated findings table

| ID | Severity | Area | Title | Evidence | Effort | Tag |
|----|----------|------|-------|----------|--------|-----|
| SEC-01 | CRITICAL | Security | Unauthenticated PATCH sets API key/provider/model | `main.py:210–230` | M | VERIFIED |
| SEC-02 | HIGH | Security | Settings UI implements de-facto BYOK contrary to Session 2 | `SettingsPage.tsx:129–138`; ROADMAP:192–194 | S–M | VERIFIED |
| SEC-03 | MEDIUM | Security | No provider allowlist; unknown providers skip model guard | `main.py:183–196` | S | VERIFIED |
| AI-01 | HIGH | AI | Duplicated LLM plumbing; 4 adapters unmigrated | evening/insights/briefing/claude files | L | VERIFIED |
| AI-02 | HIGH | AI | OpenAI is non-functional end-to-end | `pyproject.toml`; conversation `:73–78` | M | VERIFIED |
| AI-03 | HIGH | AI | No LLM timeouts/retries/rate-limit/stream | adapters (no timeout args) | L | VERIFIED |
| AI-04 | HIGH | AI | No evals / AI regression suite | tests tree inventory | L | VERIFIED |
| AI-05 | HIGH | AI | Triage context lacks titles; briefing subject attr bug | `schemas.py:39–46`; `briefing_adapter.py:49`; `AllItemsPage.tsx:87` | M | VERIFIED |
| AI-06 | MEDIUM | AI | Soft 200 responses hide LLM failures | conversation `:94–99` | S | VERIFIED |
| AI-07 | MEDIUM | AI | Prompt injection surfaces (question + item bodies) | AskRequest; claude user message | M | VERIFIED |
| AI-08 | MEDIUM | AI | No token/latency/cost observability | no usage logging | M | VERIFIED |
| AI-09 | LOW | AI | `gpt-` prefix guard wrong for modern OpenAI families | `main.py:184` | S | VERIFIED |
| ARCH-01 | HIGH | Arch | In-memory settings singleton / multi-worker unsafe | `settings.py:55–75` | M | VERIFIED |
| ARCH-02 | MEDIUM | Arch | Endpoint prefix/error-shape inconsistency | `main.py` inventory | M | VERIFIED |
| ARCH-03 | MEDIUM | Arch | Non-atomic file writes | `file_io.py:15–18` | M | VERIFIED |
| ARCH-04 | LOW | Arch | Dead `classify_work_item` import | `run_daily_ops.py:26` | S | VERIFIED |
| BE-01 | MEDIUM | Backend | Unpinned Python deps / no lockfile | `pyproject.toml` | M | VERIFIED |
| BE-02 | MEDIUM | Backend | CI Python 3.11 vs local 3.13 | `ci.yml:19`; `python --version` | S | VERIFIED |
| BE-03 | MEDIUM | Backend | No settings/ask/insights/evening API tests | tests grep | M | VERIFIED |
| BE-04 | LOW | Backend | No mypy/ruff configured | tooling search | M | VERIFIED |
| FE-01 | MEDIUM | Frontend | Gear → `/connections` | `App.tsx:93` | S | VERIFIED |
| FE-02 | MEDIUM | Frontend | Claimed FE tests missing | glob 0; CHANGELOG claims | M | VERIFIED |
| FE-03 | MEDIUM | Frontend | Monolithic CSS; mixed panel lifecycle | `index.css` size; App/Notify/Priorities | L | VERIFIED |
| FE-04 | LOW | Frontend | No fetch timeouts; TS not fully strict | `client.ts`; tsconfig | S | VERIFIED |
| CI-01 | MEDIUM | CI | Thin gates; no secret/coverage/Python lint | `ci.yml` | M | VERIFIED |
| CI-02 | LOW | CI | No pre-commit | missing configs | S | VERIFIED |
| DEP-01 | HIGH | Deploy | Not production-ready (auth, CORS, container, persistence) | inventory | XL | VERIFIED |
| DOC-01 | HIGH | Docs | Fragmented/stale docs; Session records not SoT | PROGRESS vs ROADMAP vs code | M | VERIFIED |
| DOC-02 | MEDIUM | Docs | architecture.md factual errors | routes/Pydantic/components claims | M | VERIFIED |
| DOC-03 | MEDIUM | Docs | AGENTS local-only vs Anthropic + production goal | `AGENTS.md:37–41` | S | VERIFIED |
| PROV-01 | HIGH | Provenance | Session 1–3 not attached; Session 1 missing as record | prompt + repo search | M | VERIFIED |
| PROV-02 | LOW | Provenance | `opspilot_*_mobile.html` absent; numbered refs exist | glob + design-reference | S | VERIFIED |

---

## 14. After You Finish

### 1. Files changed

| Path | Change |
|------|--------|
| — | **None (Ask mode)** |

### 2. Command output summaries

| Command | Result |
|---------|--------|
| pytest | **Not run** (Ask mode / no-write preflight missing) — UNVERIFIED-AT-RUNTIME |
| lint / build | **Not run** — UNVERIFIED-AT-RUNTIME |
| npm audit | **Not run** — UNVERIFIED-AT-RUNTIME |
| History secret search | Ran read-only `git log`/`git ls-files`/`check-ignore`; **no committed `.env`**; no clear real `sk-ant-` secret blob found; docs mention API key loading |
| Test count | **51** `test_*` functions via AST — VERIFIED |
| Python / Node | 3.13.13 / v24.14.0 — VERIFIED |

### 3. Git log/status

- **HEAD:** `41a867828c61815b50579114ec127cb80b33c3ff` (`41a8678`)
- **Branch:** `main`, clean, up to date with `origin/main`
- **Last 10 commits:** listed in §1a

### 4. Push confirmation

**N/A — read-only audit; nothing committed or pushed.**

### 5. Warnings / concerns / assumptions

1. **Operator preflight was not pasted** — runtime claims that depend on pytest/npm audit/live smoke are UNVERIFIED-AT-RUNTIME.
2. **Session records 1–3 were not attached** to the prompt; Session 1 has no discrete repo artifact. Session 2/3 reconstructed from `ROADMAP.md`.
3. Files **not fully opened** end-to-end include: complete `docs/demo.md`, `docs/glossary.md`, `docs/scheduling.md`, `docs/copilot-workflow.md`, full `sample_input.json` tail, every design-reference HTML, every FE component beyond targeted reads, full `test_api.py`, full `run_history.py` remainder, `cli.py`, ingest/normalizer internals.
4. Assumed uvicorn default bind remains loopback when started per README (not observed live this audit).
5. Prompt statement “Frontend: React 19 + TypeScript + Vite” — **CONFIRMED** via `package.json`.
6. Prompt “Current model: Anthropic Claude Haiku 4.5” — **CONFIRMED** as default string `claude-haiku-4-5-20251001`.
7. Suspected wrong/stale statements in **this repo’s docs**: FE tests exist; models are Pydantic; only three routes; components never call API; BYOK simultaneously ruled out and shipped in UI.
8. **Recommendation ≠ decision** — owner chooses direction after this baseline.

---

**Bottom line for the permanent record:** At HEAD `41a8678`, OpsPilot is a **strong local product demo with a partial AI adapter story**, blocked from production and from portfolio-grade AI-engineering signal primarily by **unauthenticated settings/key mutation**, **unfinished provider/gateway work**, and **missing evals/observability/structured-output discipline**. M0 (records) + M1 (security/key policy) should precede further feature work.
