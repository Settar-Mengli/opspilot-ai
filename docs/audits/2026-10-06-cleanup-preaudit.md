# Pre-plan audit — final cleanup (2026-10-06)

> Draft for later commit as `docs/audits/2026-10-06-cleanup-preaudit.md`.  
> **Ask / read-only.** No commits created in this audit.  
> Base: `origin/main` = `925f1aa` (PR #49 merge).

---

## A. Baseline

### A1. Git + PR #49

| Fact | Evidence |
|------|----------|
| `origin/main` | `925f1aa868960fe41ce86229d5c11de650950325` |
| Subject | `Merge pull request #49 from Settar-Mengli/mcp/github-readonly` |
| Date | 2026-10-06 14:32:57 -0400 |
| PR #49 | **MERGED** at 2026-10-06T18:32:58Z; mergeCommit = `925f1aa…`; URL https://github.com/Settar-Mengli/opspilot-ai/pull/49 |
| Local HEAD | `925f1aa…` (same as `origin/main`) |
| `git status` | `## main...origin/main` (clean) |
| Fetch note | Pruned deleted remote `origin/mcp/github-readonly` |

**Last 5 on `origin/main`:**

```
925f1aa Merge pull request #49 from Settar-Mengli/mcp/github-readonly (2026-10-06 14:32:57 -0400)
e82954c docs(mcp): record first scheduled Morning Run e2e in PART 22. (2026-10-06 14:24:18 -0400)
a06c0ef docs(mcp): restore Owner C0 result heading in D-034. (2026-10-06 14:06:29 -0400)
88c6faf docs(mcp): PART 22 B6.2 closeout after LIVE. (2026-10-06 13:57:24 -0400)
7755c3c fix(mcp): write-deny mutation test. (2026-10-06 13:13:58 -0400)
```

### A2. CI for tip `925f1aa`

| Item | Value |
|------|-------|
| CI run id | **37512168468** |
| URL | https://github.com/Settar-Mengli/opspilot-ai/actions/runs/37512168468 |
| Conclusion | **success** (all jobs: Gitleaks, Frontend Checks, Backend Tests, UI Tests) |
| Backend pytest | **659 passed**, 10 warnings, 45.41s |
| Coverage | **TOTAL 82.85%** (gate 72%; log: “Required test coverage of 72% reached. Total coverage: 82.85%”) |
| UI Tests | **191 passed**, **31 skipped** (viewport-conditional; see F1) |
| npm audit (Frontend Checks) | `found 0 vulnerabilities` (also on `npm ci`) |
| pip-audit (Backend) | `No known vulnerabilities found` |
| Gitleaks | job **success**; checkout `fetch-depth: 0` |

### A3. Alembic / open PRs / remotes

**Alembic head (CURRENT):** `0010_ops_jobs_corrections_budget` (`alembic/versions/0010_ops_jobs_corrections_budget.py:15–16`; linear chain 0001→0010).

**Open PRs (only Dependabot):**

| PR | Title | Branch tip | Checks |
|----|-------|------------|--------|
| [#41](https://github.com/Settar-Mengli/opspilot-ai/pull/41) | Bump `typescript-eslint` 8.70.1→8.71.0 | `e61eebf` | All SUCCESS; `mergeable=MERGEABLE`, `mergeStateStatus=CLEAN` |
| [#42](https://github.com/Settar-Mengli/opspilot-ai/pull/42) | Bump python minor/patch (`anthropic` + `fastapi`) | `6bd7b52` | All SUCCESS; `mergeable=MERGEABLE`, `mergeStateStatus=CLEAN` |

Both PRs base on `2131f32` (ancestor of main; **85 commits** behind tip).

**Every remote branch (other than symbolic `origin`):** see §B / Remote SHAs table below.

---

## B. Branches

| Remote branch | Tip (short) | Last commit date | Merged into main? | Commits not in main | Delete? |
|---------------|-------------|------------------|-------------------|---------------------|---------|
| `origin/b5/agentic-ask` | `9957cf4` | 2026-10-02 | **yes** | 0 | **Safe** |
| `origin/b6/morning-run` | `717391b` | 2026-10-05 | **yes** | 0 | **Safe** |
| `origin/chore/morning-workflow-dispatch` | `97ef6e5` | 2026-10-04 | **yes** | 0 | **Safe** |
| `origin/docs/b6-merge-closeout` | `8534f8d` | 2026-10-05 | **yes** | 0 | **Safe** |
| `origin/docs/owner-decisions-2026-10-05` | `63edfe8` | 2026-10-05 | **yes** | 0 | **Safe** |
| `origin/visual/b6-gallery` | `d98eb4f` | 2026-10-03 | **no** | 6 | **Decision** (see below) |
| `origin/visual/b6-gallery-2` | `ae02236` | 2026-10-04 | **no** | 10 | **Safe after owner ack** (see below) |
| `origin/dependabot/.../frontend-dev-minor-patch-…` | `e61eebf` | 2026-10-03 | **no** | 1 | **Keep until merge/close of #41** |
| `origin/dependabot/uv/python-minor-patch-…` | `6bd7b52` | 2026-10-03 | **no** | 1 | **Keep until merge/close of #42** |

### Visual gallery branches (explicit)

**`visual/b6-gallery` (`d98eb4f`)**  
- 6 commits ahead of main (harness/UI gallery work).  
- Blob compare vs `origin/main`: several paths **DIFFERENT** (e.g. `visual.spec.ts`, `AskPanel.tsx`, `SettingsPage.tsx`, `helpers.ts`); some SAME (`client.ts`, `overlays.css`, two fixtures).  
- `.github/visual-run.json` exists on this branch; **missing on main**.  
- Product landing of approved gallery is on main via `e643c16` (PART 14). Tip content is an **older scratch tree**, not byte-identical to main.  
- **Deleting loses** the ability to re-checkout that intermediate tip for historical UI Baselines re-runs. Approved PNGs / landed FE are on main.  
- **Recommend:** delete after owner confirms no pending UI Baselines job still points at `visual/b6-gallery`. Record tip SHA in cleanup PART.

**`visual/b6-gallery-2` (`ae02236`)**  
- 10 commits not in main’s ancestry, but **only file differing from main tip is** `.github/visual-run.json` (ephemeral UI Baselines config: mode `compare`, refs to this branch, artifact ids). All product/harness blobs match main (via forward-merge + land).  
- **Deleting loses** only that scratch `visual-run.json` tip (not on main by design).  
- **Recommend:** **safe to delete** once no active UI Baselines run needs `frontend_ref: visual/b6-gallery-2`. Keep SHA `ae02236` / approved run `37215651414` in PART 14 forever.

### Dependabot branches (explicit)

- **#41 / npm:** only `frontend/package.json` + lock — `typescript-eslint` ^8.70.1 → ^8.71.0. CI green on branch tip; **85 commits behind**; merge needs rebase/update onto `925f1aa`. Low risk after green CI on updated tip.  
- **#42 / uv:** `anthropic` lock 1.8.0→1.10.0 and specifier `>=0.25.0`→`>=1.10.0`; `fastapi` 0.141.1→0.142.2 (+ transitive `opentelemetry-api`). PART 20 recorded **anthropic 1.8.0** as shipped. **Not “merge now without decision”** — SDK bump needs owner acceptance + CI on rebased tip.  
- **Do not delete** these remotes while PRs are open.

### Local branches with gone remotes

Thirteen local `visual/*` mutation/determinism branches track **gone** remotes (already deleted on origin). Safe to prune locally (`git branch -d` / `-D` after owner ack). Examples: `visual/before-c5de149`, `visual/mutation-*`, `visual/determinism-*`, `visual/harness-r1`, `visual/compare-gallery`.

Local merged remotes still checked out: `b5/agentic-ask`, `b6/morning-run`, `chore/morning-workflow-dispatch`, `docs/b6-merge-closeout`, `docs/owner-decisions-2026-10-05`, `visual/b6-gallery`, `visual/b6-gallery-2`.

---

## C. Repo contents

### C1. Leftovers inventory

| Path | What it is | References | Safe to remove? |
|------|------------|------------|-----------------|
| `tmp/` (gitignored) | Local scratch: diagnose scripts (`diag_*.py`, `smoke_*.py`, `_db_check.py`, …) + `tmp/live_smoke/*.log` | `.gitignore:49`; `live_smoke_b5` / ask-send runbook expect gitignored `tmp/live_smoke/` | **Yes locally** (owner disk). Not in git. **Do not commit.** Treat logs as secret-bearing — delete, do not paste. |
| `.coverage`, `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`, `.venv/` | Tool caches / venv | gitignored | Local only; leave or wipe locally |
| `.env` | Local secrets | gitignored; **not read this audit** | Never commit / never print |
| Tracked `scripts/*` (6 files) | `capture_google_fixtures.py`, `check_fe_api_paths.py`, `export_openapi.py`, `live_smoke_b5.py`, `run_api.py`, `visual_gallery.mjs` | CI (`export_openapi`, `visual_gallery`); runbooks; tests for smoke/fixtures | **Do not delete** — load-bearing |
| `frontend/design-reference/` | Locked B1.5b HTML mockups | `frontend/design-reference/README.md`; gallery approvals | **Keep** (historical design SoT) |
| `docs/history/`, older `docs/audits/*` | Historical | AGENTS: historical only | **Do not rewrite/delete** |
| `docs/audits/2026-10-06-b7-preaudit.md` | B7 backlog revive checklist | PART 21 | **Keep** |
| Duplicate PART 18 in master record | See C2 | PART 21 carried item | Fix in cleanup (append-only options) |
| Stale “PR pending” living docs | README / ROADMAP / architecture / CHANGELOG / `.env.example` | See C5 | Truth-align in cleanup or README batch |

`git status` tracked tree is clean; leftovers are **local `tmp/`** + **remote scratch branches** + **doc drift**, not untracked tracked-path mess.

### C2. Duplicate PART 18

| Copy | Lines | SHA256 (section bytes) |
|------|-------|------------------------|
| First | **1985–2045** | `1676721fcee1bef8…` |
| Second | **2046–2106** | `1676721fcee1bef8…` |

**Byte-identical: YES** (`identical True`; equal length 3295).

**Options (append-only constraint — do not edit PART 18 bodies in place as “fix history”):**

1. **Recommended:** In cleanup PART, record “duplicate PART 18 block at 2046–2106 is accidental identical copy; treat first as canonical; second is inert duplicate.” Optionally add a one-line HTML comment / marker **only if** owner accepts a surgical deletion of the second copy in a dedicated docs commit that is explicitly framed as non-rewriting of *earlier* PARTs’ meaning (still edits the file). Strictest append-only: **leave both**, document in new PART.  
2. Surgical delete of lines 2046–2106 in cleanup docs commit (content-preserving; removes clutter).  
3. Do nothing until README batch.

**Recommend:** option **2** in cleanup batch (delete exact duplicate block; cite identical hashes in PART), or option **1** if owner wants zero edits inside the PART 18 region.

### C3. Owner machine paths in repo

| File | Path reference |
|------|----------------|
| `docs/history/session-01.md:5` | `C:\Users\setta\OneDrive\Desktop\Git Repository\opspilot-ai` |
| `docs/runbooks/llm-providers.md:205` | `cd C:\Dev\opspilot-ai` |
| `docs/runbooks/local-dev.md:14` | `cd c:\Dev\opspilot-ai` |
| `docs/audits/2026-09-28-b2-preaudit.md:316` | `cd C:\Dev\opspilot-ai` (historical audit) |

Runbook `cd` lines are intentional local-dev instructions. `docs/history/session-01.md` is historical; **do not rewrite**.

### C4. B7 still “planned” after PART 21

**Correct CURRENT framing:** B7 = **BACKLOG** (PART 21, ROADMAP, AGENTS, glossary, D-021 idle).

**Still phrased as active plan / next (stale or historical):**

| Location | Nature |
|----------|--------|
| Duplicate PART 18 remaining-order item 2 “B7 public free-tier deploy” | Historical PART body (append-only) |
| PART 19 item 2 / order | Historical; superseded by PART 21 sequencing |
| PART 20 “B7 next…” / “candidate for B7” | Historical PART body |
| Living docs that correctly say BACKLOG | ROADMAP, AGENTS, architecture BACKLOG bullets |

**No living SoT still schedules B7 as next spine batch** after PART 21 — except residual “PR pending” MCP text (C5) and historical PART language.

### C5. Stale documentation (shipped vs TARGET)

| Claim | File:lines | Reality |
|-------|------------|---------|
| MCP “PR pending owner merge” / tip `7755c3c` until merge | `README.md:7`, `ROADMAP.md:237`, `docs/architecture.md:3,148,377`, `CHANGELOG.md:20` | PR **#49 merged** → `925f1aa` |
| b6.1 “merge pending” / tip `e181818` | `docs/architecture.md:42` | Merged PR #47 → `fed71d1` (PART 21 already notes living docs should stop saying pending) |
| `.env.example` “b6.1 TARGET until C9” | `.env.example:60–61` | b6.1 **CURRENT** (PART 20/21) |
| PART 18 “First schedule … Pending” | master record 2007 / 2067 | Superseded: schedule run **37507785445** success (PART 22 / `e82954c`) |

---

## D. Dependencies and tooling

### D1. Open Dependabot PRs

| PR | Updates | CI | Safe to merge now? |
|----|---------|-----|-------------------|
| **#41** | `typescript-eslint` 8.70.1→8.71.0 (+ lock) | Green on tip `e61eebf` | **Conditionally yes** after rebase onto `925f1aa` and green CI; low risk |
| **#42** | `anthropic` 1.8.0→1.10.0; `fastapi` 0.141.1→0.142.2 | Green on tip `6bd7b52` | **Owner decision** — anthropic was pinned/recorded at 1.8.0 in PART 20; rebase + re-run CI required; treat as intentional SDK bump, not drive-by |

### D2. Unused dependencies

**CANNOT-VERIFY exhaustively** without depcheck/knip (not run). Spot check: `mcp`, `anthropic`, `fastapi`, frontend React/Playwright/Vitest packages are referenced. No proven unused dep found in this audit.

Owner commands if desired:

```powershell
cd c:\Dev\opspilot-ai\frontend; npx knip
cd c:\Dev\opspilot-ai; uv run pipdeptree
```

### D3. Audit status from CI tip run 37512168468 (not a fresh local run)

| Gate | Result |
|------|--------|
| `npm audit --audit-level=moderate` | `found 0 vulnerabilities` |
| `pip-audit` on frozen prod export | `No known vulnerabilities found` |

---

## E. Secrets hygiene

### E1. Secrets never committed (as far as CI history scan shows)

- Tip CI **Gitleaks** job **success** with `fetch-depth: 0` (full history checkout) on run **37512168468**.  
- This audit did **not** install/run gitleaks locally.

Owner confirmation command:

```powershell
cd c:\Dev\opspilot-ai
# install gitleaks 8.30.1 per .github/workflows/ci.yml pin, then:
gitleaks detect --source . --verbose --log-opts="--all"
```

### E2. Documented env names (`.env.example`) + flags

**Active / documented (set or commented as optional):**  
`DATABASE_URL`, `INFERENCE_PROVIDER_ORDER`, `GEMINI_*`, `GROQ_*`, `MISTRAL_*`, `OPENROUTER_*`, `CLOUDFLARE_*`, `OLLAMA_BASE_URL`/`OLLAMA_MODEL`, budget `OPSPILOT_BUDGET_*`, `OPSPILOT_ANTHROPIC_ENABLED`, `ANTHROPIC_API_KEY`/`ANTHROPIC_MODEL`/`OPSPILOT_ANTHROPIC_*`, LLM policy/trace/circuit, Google OAuth + `TOKEN_ENCRYPTION_KEY`/`OPSPILOT_SESSION_SECRET`, `OPSPILOT_DEMO_MODE`, send allowlist/caps, Ask caps, GitHub MCP set, CSRF/CORS/cookie, `OPSPILOT_SYNC_TRIAGE_CAP`.

**Explicitly retired in docs (not runtime):**  
`OPSPILOT_AI_API_KEY` / `OPSPILOT_AI_PROVIDER` / `OPSPILOT_AI_MODEL` (`.env.example:110`; still tested as ignored in `tests/unit/test_ai_settings_retirement.py`).  
`OPSPILOT_ANTHROPIC_BUDGET_TOKENS` / `_USD` (D-023 historical table; PART 20).

**Used in code/workflows but not listed in `.env.example` (doc gap, not necessarily retired):**  
`TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID`, `OPSPILOT_MORNING_FORCE`, `OPSPILOT_SIMULATE_GOOGLE_REAUTH`, `OPSPILOT_MORNING_REQUEST_CEILING`, `OPSPILOT_SYNC_REQUEST_CEILING`, `OPSPILOT_BRIEF_REQUEST_RESERVE`, `OPSPILOT_JOB_*`, `OPSPILOT_FE_ORIGIN`, `OLLAMA_API_KEY`, `OPSPILOT_LIVE_ALLOW_NONLOCAL_DB`, `OPSPILOT_GIT_SHA`, task-scoped `GEMINI_MODEL_*` / etc.

### E3. Owner local items — gallery folders + PowerShell Neon URL

**Find gallery / visual download dirs:**

```powershell
Get-ChildItem C:\Dev -Directory -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -match 'gallery|visual|b6-gallery|playwright|artifact' }
Get-ChildItem C:\Temp,$env:TEMP -Directory -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -match 'gallery|visual|b6|opspilot|playwright' }
Get-ChildItem C:\Dev\opspilot-ai\tmp -Recurse -ErrorAction SilentlyContinue |
  Select-Object FullName
```

This audit’s quick scan under `C:\Dev` / `C:\Temp` / `$env:TEMP` found **no** matching gallery folder names (only repo `tmp/`). Owner may still have downloads elsewhere.

**Clear PowerShell history (Neon URL):**

```powershell
# Inspect (do not paste URL into chat)
Select-String -Path (Get-PSReadLineOption).HistorySavePath -Pattern 'neon\.tech|DATABASE_URL|postgresql' -SimpleMatch:$false
# Clear PSReadLine history file
Remove-Item -Force (Get-PSReadLineOption).HistorySavePath -ErrorAction SilentlyContinue
# New empty history
New-Item -ItemType File -Path (Get-PSReadLineOption).HistorySavePath -Force | Out-Null
Clear-History
```

**Plain statement:** Clearing history is **not sufficient**. A Neon connection string in history is a **credential exposure**. **Rotate** the Neon role password / connection string in the Neon console, update local `.env` and GitHub Actions secret `OPSPILOT_DATABASE_URL`, then clear history. (PART 21 already: “Neon URL may be in PowerShell history → **rotate** credential.”)

### E4. Gemini API key exposed in local logs (MCP live run)

**Rotate:** Google AI Studio / Cloud console → invalidate old key → create new key → put **only** in local `.env` and (if used) GitHub Actions secret `GEMINI_API_KEY`. Restart local API.

**Repo update after rotate:** **None required** if the key was never committed (`.env` gitignored; workflows reference `${{ secrets.GEMINI_API_KEY }}`). Delete local secret-bearing logs under `tmp/live_smoke/` without pasting contents. No code/ADR change unless docs incorrectly embedded a key (**none found** in tracked files this audit).

---

## F. Test and CI health

### F1. Skipped / xfail / quarantine

- **pytest:** no `@pytest.mark.skip` / `xfail` / quarantine markers under `tests/` (`git grep` exit 1 / empty).  
- **Playwright:** intentional `test.skip` by viewport (not quarantine):
  - `desktop-layout.spec.ts` — desktop-only vs mobile-only  
  - `overlay-stack.spec.ts` / `production-effects.spec.ts` — skip at `chromium-1280` (Ask docked)  
  - `visual.spec.ts:407–410` — desktop visual states only on `chromium-1280`  
- UI tip run: **31 skipped**, **191 passed**.

### F2. Workflow steps dead/duplicated

- Active workflows: `ci.yml`, `morning.yml`, `ui-baselines.yml` only.  
- CI structure is coherent (gitleaks / backend / frontend / UI). Upload Playwright report is `if: failure()` — skipped on green (expected).  
- No duplicate morning workflow found.  
- `ui-baselines.yml` still materializes `scripts/visual_gallery.mjs` and optional `visual-run.json` from branch tips — needed for gallery flow; not dead.

### F3. Morning workflow leftovers from debugging

- `morning.yml` is clean: schedule `0 12 * * *` + `workflow_dispatch`, Anthropic forced off, no debug/TODO/scratch matches.  
- First schedule cancelled historically (`37368659012`); successful schedule e2e recorded (`37507785445` on `c398457`, PART 22). No debug residue observed in the workflow file.

---

## G. Findings and options (TARGET)

### G1. Cleanup inventory (value-ranked)

**High value (reviewer / SoT clarity)**  
1. Truth-align living docs after PR #49 (README, ROADMAP, architecture, CHANGELOG “PR pending”).  
2. Delete merged remote feature/docs branches (0 commits lost).  
3. Resolve duplicate PART 18 (document + optional surgical delete).  
4. Owner secret hygiene: rotate Neon + Gemini; wipe `tmp/` logs; clear PS history.  
5. Decide Dependabot #41/#42 (rebase; #42 needs anthropic/fastapi accept).

**Medium**  
6. Delete `visual/b6-gallery-2` (only ephemeral `visual-run.json`).  
7. Delete `visual/b6-gallery` after confirming no UI Baselines pointer.  
8. Prune local gone `visual/*` branches.  
9. Fix `.env.example` “TARGET until C9” → CURRENT wording.  
10. Optionally document morning/Telegram env names in `.env.example` or runbook only.

**Cosmetic / low**  
11. Local `tmp/` diagnose scripts (already gitignored).  
12. Machine path in historical `docs/history/session-01.md` (leave).

### G2. Must NOT clean

- `docs/history/*`, older audits, ADR bodies, PART 0–22 bodies (except optional identical PART 18 duplicate delete with explicit record).  
- `frontend/design-reference/`, committed `-linux` baselines, `scripts/visual_gallery.mjs`, `live_smoke_b5.py`, Alembic versions.  
- B7 backlog artifact `docs/audits/2026-10-06-b7-preaudit.md`.  
- Open Dependabot branches while PRs open.  
- Rewriting historical “B7 next” inside old PARTs.

### G3. Deletion risks + reversibility

| Action | Risk | Reversible? |
|--------|------|-------------|
| Delete merged remotes | Low | Recover SHA from PART/PR until GC; `git fetch` won’t restore deleted remote without recreate |
| Delete `visual/b6-gallery-2` | Low (only visual-run.json) | Tip `ae02236` recoverable if not GC’d; PART 14 has SHA |
| Delete `visual/b6-gallery` | Medium (unique tip blobs) | Same — keep SHA note before delete |
| Delete PART 18 duplicate lines | Low (identical) | Revert docs commit |
| Wipe `tmp/` | Low for repo; may lose local debug | Irreversible for files |
| Merge #42 without review | Medium (SDK) | Revert merge commit |

### G4. Owner decisions (with recommendation)

| # | Decision | Recommend |
|---|----------|-----------|
| 1 | Delete merged remotes (`b5`, `b6`, `chore/morning…`, two `docs/*`)? | **Yes** |
| 2 | Delete `visual/b6-gallery-2`? | **Yes** (after no active baselines run) |
| 3 | Delete `visual/b6-gallery`? | **Yes** after confirm no UI Baselines ref; accept loss of intermediate tip |
| 4 | PART 18 duplicate: leave vs surgical delete? | **Surgical delete** of second copy + note in cleanup PART |
| 5 | Dependabot #41? | **Merge after rebase** onto `925f1aa` |
| 6 | Dependabot #42 (anthropic 1.10 + fastapi 0.142)? | **Defer or explicit accept** — not silent; re-verify against PART 20 pin |
| 7 | Rotate Neon + Gemini now? | **Yes** (Neon required; Gemini required if logs exposed key) |
| 8 | Include living-doc truth-align in cleanup vs README batch? | **Cleanup** for “PR pending” / MCP merged; README batch still owns professional README |

### G5. One batch or split? Wait for README/demo?

**Recommend: one cleanup batch** (PART 21 step 2) covering: branch deletes, PART 18 duplicate, living-doc tip truth-align (MCP merged), `.env.example` CURRENT wording, Dependabot decision execution, owner local hygiene commands (owner-run).  

**Do not wait** for README/demo for branch deletes / secret rotation / PART 18 — those unblock a cleaner README/demo.  

**Split only if** #42 anthropic bump is treated as its own mini deps batch (safer). Gallery PNG/README polish stays in **README** step.

---

## Report contract

### 1. Files table (opened / why / key evidence)

| File | Why | Key evidence |
|------|-----|--------------|
| `OPSPILOT-MASTER-RECORD.md` | PART 18 dup, PART 19–22 order | 1985–2106 identical; 2323+ PART 21 cleanup; 2366 dup note |
| `ROADMAP.md` | B7 / MCP status | B7 BACKLOG; MCP “PR pending” stale `:237` |
| `README.md` | Living CURRENT claims | `:7` PR pending MCP |
| `docs/architecture.md` | CURRENT/TARGET drift | `:3,:42,:148,:377` |
| `CHANGELOG.md` | Stale PR pending | `:20` |
| `.env.example` | Env catalog + stale TARGET | `:60–61`, `:110` retired |
| `pyproject.toml` / `uv.lock` | Deps / anthropic pin | anthropic 1.8.0 locked |
| `frontend/package.json` | typescript-eslint pin | `^8.70.1` |
| `.github/workflows/ci.yml` | CI gates | gitleaks depth 0; pip-audit; npm audit; cov 72 |
| `.github/workflows/morning.yml` | Debug leftovers | Clean schedule+dispatch |
| `.github/workflows/ui-baselines.yml` | visual-run / gallery | Uses `visual_gallery.mjs` |
| `.gitignore` | `tmp/` policy | `:49` |
| `alembic/versions/0010_*.py` | Head | revision `0010_…` |
| `frontend/e2e/*spec.ts` | skips | viewport skips |
| `docs/history/session-01.md` | machine path | `:5` |
| `docs/runbooks/local-dev.md`, `llm-providers.md` | `C:\Dev\…` | cd instructions |
| `docs/adr/D-021`, `D-023` | B7 backlog / retired budget | idle / L4 |
| `AGENTS.md` | B7 dropped | `:123` |

### 2. Command summaries

| Command | Exit | Summary |
|---------|------|---------|
| `git fetch origin --prune` | 0 | Pruned `origin/mcp/github-readonly` |
| `git rev-parse` / `log` / `status` | 0 | main=`925f1aa`, clean, last 5 as above |
| `gh pr view 49` | 0 | MERGED |
| `gh run list --commit 925f1aa…` / `gh run watch 37512168468` | 0 | CI **success** |
| `gh run view … --log` | 0 | 659 passed; cov 82.85%; npm 0 vuln; pip-audit clean; UI 191 pass / 31 skip |
| `git for-each-ref` + merge-base checks | 0 | Branch table §B |
| `gh pr list` / `view 41|42` | 0 | Two open Dependabot PRs, checks green, base `2131f32` |
| PART 18 Python hash compare | 0 | identical |
| `git diff name-status` gallery branches | 0 | gallery-1 many diffs; gallery-2 only `visual-run.json` |
| Local `Get-ChildItem` galleries | 0 | No matching dirs under quick `C:\Dev`/`Temp` scan |
| `git grep` pytest skip markers | 1 | None |

### 3. git log (last 5) and status

See §A1. Status: `## main...origin/main`.

### 4. Remote SHAs

| Ref | Full SHA |
|-----|----------|
| `origin/main` | `925f1aa868960fe41ce86229d5c11de650950325` |
| `origin/b5/agentic-ask` | `9957cf492c82f52c599a29352295ecefe63fba1a` |
| `origin/b6/morning-run` | `717391b4109fe9148c14399e99f31914bb02a4ce` |
| `origin/chore/morning-workflow-dispatch` | `97ef6e58eeac41d0c90626097cef2997cc2aefd0` |
| `origin/docs/b6-merge-closeout` | `8534f8d261fdfdcee42e5eb1ab5184257aa2ddfa` |
| `origin/docs/owner-decisions-2026-10-05` | `63edfe852f3b0ca9c1e082fbf60be6b1b716d020` |
| `origin/visual/b6-gallery` | `d98eb4f405eee54c8489d44d30438401143312ca` |
| `origin/visual/b6-gallery-2` | `ae02236a2ee7500ff4fb1986c0e9413273f59bd4` |
| `origin/dependabot/npm_and_yarn/frontend/frontend-dev-minor-patch-6dde1de8b4` | `e61eebf26cc1787602001cf5b7a499ad136e291d` |
| `origin/dependabot/uv/python-minor-patch-09f47d5abd` | `6bd7b52146ddfa36b5ecc0225b1c7fd7ec89318a` |

### 5. CI run id for main tip

**37512168468** — **success**.  
**No commits created in this audit.**

### 6. Deviations from this prompt

- Initial PowerShell `for`/`grep` one-liner failed; re-ran with PowerShell-safe loops.  
- Did not read `.env`.  
- Did not run live LLM / GitHub MCP / Neon / Google / Telegram.  
- Did not install local gitleaks; relied on CI Gitleaks + owner command.  
- Did not exhaustively prove unused npm/py deps (CANNOT-VERIFY).  
- Quick filesystem search did not locate owner gallery folders under `C:\Dev`/`Temp` (owner should still run find commands).  
- Did not print or open `tmp/live_smoke` log contents.

### 7. CANNOT-VERIFY

| Item | Owner command |
|------|----------------|
| Local gitleaks full-history beyond CI | `gitleaks detect --source . --verbose --log-opts="--all"` (pin 8.30.1 as in `ci.yml`) |
| Unused frontend/Python deps | `npx knip` in `frontend/`; `uv run pipdeptree` / manual import graph |
| Exact PowerShell history hit for Neon URL | `Select-String -Path (Get-PSReadLineOption).HistorySavePath -Pattern 'neon\.tech'` |
| Gallery folders outside searched roots | Expand `Get-ChildItem` to Downloads, Desktop, OneDrive |
| Whether any UI Baselines workflow_dispatch still targets gallery branch names | `gh run list --workflow="UI Baselines" --limit 10` + inspect `visual-run.json` inputs |
| Dependabot #41/#42 CI after rebase onto `925f1aa` | Rebase/update branch; wait for new CI |

---

**STOP.** No plan, no code, no deletions.
