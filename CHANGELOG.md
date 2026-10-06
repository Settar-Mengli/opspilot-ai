# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog,
and this project follows Semantic Versioning principles for release tags.

## [Unreleased]

### Fixed

- **B5 live smoke recorded:** owner-run 2026-10-02 — default PASS; `--send` on `cb452e0` FAIL (no send, `recipient_not_allowlisted`); `--send` on `6eef4c4` PASS (1 real send). OD-B5-8 + STOP VISUAL closed; **merged** via PR #40 → `2131f32`.
- **B5 live smoke pin:** `live_smoke_b5.py` selects a self-sent gmail work item, pins Ask to that id, verifies draft recipient == operator before approve, prints approve/sync/ask failure codes + request id, writes API child logs under gitignored `tmp/live_smoke/`.
- **B5 STOP VISUAL closed:** owner quote `gallery approved` — 2026-10-02; UI Baselines before **37053916564** / compare **37054725997**; 8 baselines approved (incl. 375 ask-error + connections); `MAX_DIFF_PIXELS` unchanged.
- **B5 post-audit fix-pass 2:** classify pre-POST Gmail failures as `gmail_unavailable_not_sent` (503, re-approvable, not capped); HITL last-resort never bare-500; real AskDock↔AskPanel remount tests; token_error/llm_turns behavioural fixtures; Gmail truncate second-sync assert; pytest refuses non-local `DATABASE_URL`; PART 12 byte-restored.
- **B5 post-audit fix-pass:** Gmail send single-attempt + `send_outcome_unknown` (counts toward daily cap); Calendar truncate clears syncToken + full-window absence reconcile; Gmail truncate-without-hid → full list + `gmail_truncated`; fixture behavioural loads + widened safety scan; live_smoke `--send`/preflight; typed `SyncResponse` OpenAPI; registry + PART 13.

### Added

- **b6.1 Anthropic operator switch (LIVE PASS 2026-10-05; PR pending merge):** operator-authorized Anthropic for Ask SSE + Sync drain triage; off by default; never visitors; prepaid ledger reserve/reconcile + CLI `anthropic_budget show/set`; `open_reservations` on show; startup refuse ENABLED∧DEMO; morning preflight refuse; D-023 b6.1 addendum CURRENT for shipped+LIVE clauses; PART 20. Tip `e181818` CI 37386884550; suite 622 passed / cov 82.91%.
- **B6 Morning run merged** (PR #44 → `eae1a9a`, merge CI [37263038965](https://github.com/Settar-Mengli/opspilot-ai/actions/runs/37263038965) success; LIVE PASS 2026-10-04): in-runner GHA morning job + Telegram counts-only; Sync 202/poll drain; ops_jobs lease/reap/fence; triage corrections + failed-draft reopen; F-05 plumbing; Alembic **0010**; C14 schedule `0 12 * * *` + `workflow_dispatch` (first schedule cancelled by runner non-acquire — PART 20; manual dispatch quiet-day success). PART 14–18. **Next after b6.1 merge:** **B7**.
- **B5 Agentic Ask + HITL send** (merged PR #40 → `2131f32`): JSON-emulated tool loop (D-031); `POST /ask/stream` SSE (D-032); draft edit/approve + allowlist + DEMO_MODE (D-033); `gmail.send`; Alembic **0009**; Gmail deleted/SPAM sync + pagination; Calendar pagination; FE per-attempt idempotency; sticky final provider; `live_smoke_b5`; fixture-safety gate; PART 13.
- **B3.1 complete** (branch `b3.1/live-remainder`): live eval guards; docs truth; CF D5 + CF combined (60/60, F1 0.706 n=40); OpenRouter **partial** D6 (triage n=15, F1 0.619; ASR N/A). **D-B31-4 amended 2026-10-01:** OR D7–D9/D10 + OR combined **cancelled** to unblock **B5**. PART 12. Merged PR #39 → `1a6fe7d`.
- **B4 merged** to `main` (PR #37 → `c6e677c`, 2026-10-01); PART 11 closeout; B3.1 then **B5**.
- **B4 Real Gmail + Google Calendar (branch `b4/gmail-calendar`):** OAuth PKCE loopback + Fernet refresh in `bytea`; SyncCursor; Meeting table; DEMO_MODE; operator session cookie + CORS credentials (A1 / D-030); hermetic Google fakes; Connections connect/sync/disconnect; WeekPanel from calendar; UI F-INS/NB-4/NB-3; STOP VISUAL baselines; PART 10. **STOP LIVE complete** on Neon (connect, incremental sync, capped triage 50/50; G1–G7).
- **B3 evals + red-team (merged PR #36 → `3eb7baf`):** hermetic corpus N=40 + red-team N=20; rules macro-F1 floor **0.30**; D-028/D-029; live single-provider leaderboard (Gemini/Groq/Mistral 60/60; Cloudflare D4 **partial 33/60**); D-LIVE-1..11 + D-GROQ/D-MISTRAL/D-CF-WRITE deviations in PART 9; pre-closeout CF/OR smokes (not merged into day artifacts). Remaining CF/OR live rows closed in **B3.1** (OR partial).
- **B2.1 Hardening + truth:** register + Corrections; Node 24.15 / ubuntu-24.04 / Dependabot ignores; recursive meta redaction; OpenRouter `:free` runtime gate; X-Request-ID validation; redacted LLM service logs; dead adapter delete; shared HTTP/soft-deny helpers; OBS request_id (thread-safe) + access/500 logs; `0005` `ix_run_artifacts_name`; README proof pack; design-decisions + issue/PR templates; PART 8.
- **B2 LLM gateway + traces:** hand-rolled `llm/` gateway (Gemini REST + OpenAI-compatible providers + D-023 Anthropic gate); `LlmCall` / budget counters; services for ask/evening/insights; gateway triage + briefing; runs pagination + `X-Request-ID`; F-03/F-09; timestamptz migrate; `llm_discover` job; runbook `docs/runbooks/llm-providers.md`; PART 7; ADR addenda D-012/D-013/D-019/D-023. **Env migration:** retire `OPSPILOT_AI_*`; use `INFERENCE_PROVIDER_ORDER` + per-provider keys/models + `OPSPILOT_BUDGET_*` (owner-approved 2026-09-29 defaults in `.env.example`). **Code defaults** aligned with C11 via `opspilot.llm.model_defaults` (OpenRouter keeps `:free`).
- **B1.5b desktop layout:** ≥1280 three-pane (primary rail + content + Ask dock 380px); Ask dual-mode (docked ↔ modal); All Items list+detail (default first urgent); design-reference mockups 11–16; temporary `B15B_DESKTOP_HOLD` then removed with refreshed `*-chromium-1280-linux.png` baselines; PART 6; D-026 addendum.
- **B1.5a UI safety net:** Playwright 1.55 visual/e2e/axe (container-only `-linux` baselines + Google WOFF2 fixtures); CI UI Tests + UI Baselines workflow; CSS partials; overlay stack (Escape/scroll/focus; PortalOverlay removed); U4 hygiene; F-06 path jail; deprecate `opspilot.api.main`; ADRs D-026/D-027; PART 4 (+ 2026-09-27 revision: C-BASE, per-state tol, settle exclusions, production-effects e2e).
- **B1 hermetic foundation:** `OPSPILOT_FORCE_RULES` + pytest-socket; uv lock / Python 3.13 / PEP 735; Compose+CI Postgres; **sync** SQLAlchemy/Alembic (`0002` `runs.finished_at` index); X5 importer; `/api/v1` Postgres-only runs (CLI `--output` files only); error envelope; AI-05 lite `subject_or_title`; Settings without `api_key_preview`; FE `/api/v1` + TS strict + vitest; gitleaks **v8.30.1** + Dependabot; pre-commit; coverage fail-under **72** (CI TOTAL 74.84%); Node 24; PART 3 + D-010/D-025 revised.
- **B0 docs lock + fix pass:** session history, audit corpus, master record PART 0–2, ADRs D-001–D-024, architecture CURRENT/TARGET, ROADMAP B0–B7, AGENTS plan gate, runbooks (local-dev, zero-spend, free-tier, GHA morning, OAuth re-auth), glossary updates.
- Session 3 (already on main): provider seam; frontend settings; SettingsPage lint fix.

### Changed

- **Dependabot (post-B2):** #21 `actions/upload-artifact` 7.0.1; #22 frontend-dev minor/patch group; #25 jsdom 30.1.1; #27 `@testing-library/jest-dom` 7.0.1.
- **DEP-1 dependency hygiene:** npm security floors (vite 8.0.16, postcss 8.5.23, browserslist 4.28.7, brace-expansion 5.0.9, baseline-browser-mapping 2.11.0, nanoid 3.3.18, vitest 4.1.11); Playwright **1.55.1** + `v1.55.1-jammy` image pins; React 19.3.0 (+ types); GHA checkout/setup-node/setup-uv majors; eslint/globals; psycopg/setuptools floors; Dependabot grouping. PART 5. Deferred: Vitest 5, Playwright 1.63.
- **B1.5b CI:** Frontend Checks `npm audit --audit-level=moderate` (no `--omit=dev`).

- Settings are env-only / read-only UI (PATCH removed). Coverage ratchet-only from 67.
- Roadmap IDs are **B0–B7** (+ **B1.5a/b** UI batches); owner decisions D1–D12 corrected in master record; B6 morning job in-runner (D-011); package layout D-024.
- X8 panel lifecycle started in B1.5a; agent surfaces finish on B1.5b layout in B5.

### Security

- **DEP-2:** bump transitive `brace-expansion` override `5.0.9` → `5.0.12` (Dependabot alert #18 / GHSA-q2hr-2g5m-vwhr).

### Fixed

- **B2 structured outputs (S1–S4):** Gemini `responseSchema` conversion (inline `$ref`/`$defs`, preserve property names); Groq-strict `additionalProperties:false`; JSON fence extraction; reject empty insights on non-empty queues; 400→`json_object` retry; redacted HTTP/parse meta on `LlmCall`.
- V6 briefing adapter uses `subject_or_title`.
- Changelog no longer claims a shipped frontend unit/component test suite prior to B1 (Vitest smoke added in B1).

---

## Prior Unreleased (restored from main)

### Added

- Repository trust and governance foundation files.
- Initial CI skeleton workflow for basic repository validation on push and pull requests.
- Hardened input schema validation for loader-level JSON and field-shape checks.
- Structured logging helpers and pipeline lifecycle logging events.
- User-facing CLI error handling with deterministic exit code for recoverable failures.
- Unit tests for loader validation and CLI failure behavior.
- Deterministic `urgency_reason`, `category_reason`, and `sentiment_reason` fields in triage output.
- Improved executive briefing Top Priorities formatting to include item ID and title.
- Updated unit and integration tests for explainability output and briefing formatting.
- FastAPI-based local API layer (`src/opspilot/api/main.py`)
- Endpoints: `/health`, `/run`, `/briefing`, `/triage`
- OpenAPI/Swagger docs
- API tests (`tests/api/test_api.py`)
- Updated README with API usage and endpoints
- React + Vite + TypeScript frontend in `frontend/` for local command center experience
- Command center routes: Dashboard, Triage Explorer, Executive Briefing
- Header health indicator and global API unavailable banner based on `GET /health`
- Explainability drawer in triage explorer showing urgency/category/sentiment reasons
- Frontend env template `frontend/.env.example` for `VITE_API_BASE_URL`
- Immutable local run-history artifacts under `data/history/runs/YYYY/MM/DD/run-YYYYMMDD-HHMMSS-sss/`
- Run metadata artifact `run.json` per successful run
- Run-history API endpoints:
	- `GET /runs`
	- `GET /runs/{run_id}`
	- `GET /runs/{run_id}/triage`
	- `GET /runs/{run_id}/briefing`
- Frontend historical snapshot support via shared run selector and `?run_id=` query parameter
- Dashboard run history panel and latest/historical status context badge
- Executive Briefing "Since Last Run" delta section comparing priority counts (`critical`, `high`, `medium`, `low`) to the immediately previous run
- Executive Briefing "Recent Trend (Last 7 Runs)" section summarizing deterministic high-risk (`critical + high`) counts and net change
- Vitest + Testing Library installed as FE tooling baseline (no \*.test.*\ / \*.spec.*\ under \rontend/src\ as of HEAD !a8678\ — prior changelog overstated a shipped FE test suite)
- API tests for metadata allow-listing and artifact-name edge-case handling
- API tests for local-origin CORS preflight behavior

### Changed

- Hardened API run contract in `src/opspilot/api/main.py`:
	- `date` is validated by API request schema
	- subprocess execution uses `sys.executable`
	- `input_file` is restricted to filenames under `data/raw`
	- subprocess execution now has a bounded timeout for reliability
- `/triage` now returns parsed JSON payloads instead of raw JSON strings
- `/run` now returns safe structured error payloads and avoids exposing raw stderr to clients
- Strengthened API tests in `tests/api/test_api.py` for JSON shape, timeout handling, subprocess failure behavior, and invalid date input
- Cleaned duplicated/stale sections in `README.md` and aligned wording to CLI + local API
- Added a short Security & Reliability section to `README.md`
- Added explicit restart handoff section to `PROGRESS.md`
- Moved `fastapi` and `uvicorn[standard]` to runtime dependencies in `pyproject.toml`
- Expanded README run instructions to include local frontend startup and API/UI flow
- Updated architecture and demo docs to include command center UI walkthrough
- Pipeline now writes immutable run artifacts while preserving latest-output compatibility in `data/output/`
- Frontend pages now support both Latest and Historical run contexts without adding new routes
- Briefing delta markers now use ASCII-only output for terminal compatibility:
	- `0` for no change
	- `+N` for increase
	- `-N` for decrease
- CI workflow now runs backend `pytest -q` and frontend `npm ci`, `npm run lint`, and `npm run build` on push and pull request
- Run-history metadata API responses now sanitize `input_file`, `output_dir`, and `history_dir` for `GET /runs` and `GET /runs/{run_id}`
- Expanded API metadata safety tests to assert sanitized fields are excluded and artifact names remain path-safe
- Added API test coverage to reject traversal-like run IDs for `GET /runs/{run_id}` metadata endpoint
- Run-history metadata responses now use explicit allow-listed key shaping at API boundary
- Artifact names in metadata responses now drop invalid/path-like/empty/unexpected values defensively
- CORS policy now explicitly allows `GET` and `POST` for local UI origins only, with credentials disabled
- README and docs now include local-first security checklist, reproducible validation flow, scheduling status clarity, and roadmap-only integration notes
- `.gitignore` now includes frontend generated artifacts and local runtime log hygiene
