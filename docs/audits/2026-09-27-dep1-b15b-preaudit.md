# Pre-audit: dependency hygiene + B1.5b readiness

**Repo:** `main` @ `d1c57e0` (Merge PR #18). Ask mode — no writes.

---

## 0. Verdict + recommended order

**Verdict:** Do a **consolidated dependency / security PR series first**, then plan **B1.5b** only after mocks are owner-approved (D-026 U8). Do **not** merge Dependabot Playwright #19 as-is before desktop work.

| Order | Work | Why |
|------|------|-----|
| 1 | Security + low-risk dep bumps (npm transitive + vite patch floor + vitest 4.1.11; optional GHA majors) | Clear Dependabot alerts without layout churn. VERIFIED alerts are all `development` scope. |
| 2 | Playwright **1.55.1** (not 1.63.0) **or** defer Playwright until after B1.5b | Alert #15 needs ≥1.55.1; #19 jumps to 1.63.0 + Chromium 153 → almost certain baseline regen (D-026 U9). |
| 3 | B1.5b mockups → STOP → owner approve → layout code | ROADMAP + D-026 U8. Existing `01-dashboard-desktop.html` is still a 680px card, not three-pane. VERIFIED. |

---

## 1. Part A — Dependency hygiene

*(Executed as batch DEP-1, PR #20, merged at `5e75a50`. Full Part A analysis is recorded in OPSPILOT-MASTER-RECORD.md PART 5 and the PR #20 description; summary retained here.)*

- All 10 open Dependabot alerts were npm `development` scope: playwright (<1.55.1), vitest/@vitest/mocker (<4.1.11), baseline-browser-mapping (<2.11.0), browserslist (≤4.28.6), postcss (≤8.5.17, ≤8.5.22), brace-expansion (≥3.0.0 <5.0.7), vite (≥8.0.0 ≤8.0.15).
- Dependabot #19 proposed Playwright 1.63.0 (Chromium 153) — not a security-minimal bump; 1.55.1 changes Chromium 140.0.7339.16 → 140.0.7339.186.
- Coordinated Playwright changes required: package + lock, `mcr.microsoft.com/playwright` image pin in `ci.yml` and `ui-baselines.yml`, runbook `$PIN`, and D-026 U9 flow if screenshots change.
- GHA majors (#3–#5): Dependabot SHA pins + version comments correct; CI-only risk.
- Vitest 5 (#10): major; deferred. React 19.3 (#11): take with matching react-dom.
- Recommended dependabot.yml: grouped minor/patch per ecosystem; majors ungrouped; Playwright isolated in its own groups; security separate from version-update groups.

---

## 2. Part B — B1.5b readiness

### B1. Current desktop reality (1280 / 768)

**Evidence:** committed `*-chromium-1280-linux.png` / `*-768-linux.png` (19 states each), CSS partials, `App.tsx`.

**Shell (all routes):** `app-shell` + sticky `top-nav` (Brand | HealthBell | AssistantPill | Connections gear) + `content-shell` (`max-width: 1100px; margin: 0 auto` — `shell.css:32-35`) + overlays. **No left rail. No docked Ask.** VERIFIED `App.tsx:86-137`.

| Viewport | Layout today | Ask | Dock |
|----------|--------------|-----|------|
| **1280** | Single centered column; large empty side gutters. Dashboard greeting + hero + tile grid; Settings text link in content. Ask = **centered modal** over dimmed chrome (`ask-empty-chromium-1280-linux.png`). Items = list page in same column (`items-chromium-1280-linux.png`). | Modal (`useOverlay` + `role="dialog"`) | Hidden (`mobile-dock` base `display: none`) |
| **768** | Same single-column product chrome; dashboard tiles similar to desktop but **mobile dock visible** at bottom (Ask pill + mic) — VERIFIED `dashboard-chromium-768-linux.png` + `mobile.css:2-9` (`max-width: 768` enables dock `!important`) | Modal when opened from tiles | Visible |

**Screen inventory (visual states, all three viewports):** onboarding, dashboard, dashboard-error, priorities-open, week-open, ask-empty, ask-with-messages, ask-error, evening-open, evening-error, notify-open, items, insights, insights-error, briefing, connections, connections-modal, settings, api-down-banner. VERIFIED `visual.spec.ts` + snapshot dir (19×3).

**Dashboard CSS:** `.dashboard-redesign { max-width: 600px }` (`dashboard.css:2-6`) — nested constraint inside 1100px shell. Matches “thin desktop overlay” from ui-audit. VERIFIED.

**Existing design-ref `01-dashboard-desktop.html`:** still a **680px centered card** on dark page chrome — **not** three-pane. VERIFIED `design-reference/01-dashboard-desktop.html:12-13,50-52`.

---

### B2. Re-validate ui-audit §6 vs NEW code

| §6 proposal (audit) | D-026 / ROADMAP lock | Code today | Gap |
|---------------------|----------------------|------------|-----|
| ≥1280 three-pane (rail + content + docked Ask) | U1/U2/U8; ROADMAP B1.5b | Single column + modal Ask | **Build in B1.5b** |
| Tablet 769–1279 single centered column | U2 | Effectively already (shell max 1100; no rail) | Formalize; avoid accidental 1024 “soft 2-pane” unless owner wants audit’s optional tier |
| Phone ≤768 pixel-identical | U2/U4 | Locked by baselines + dock | **Must not change** without owner |
| Settings in rail; gear → Connections; mobile Settings stays | U1/U3/U6/U7 | Gear = Connections (`App.tsx:93`); Settings route + dashboard link | Rail Settings is new chrome ≥1280 only |
| Escape / overlay stack | audit + B1.5a | `useOverlay` Escape stack, scroll refcount, focus trap | VERIFIED `useOverlay.ts` |
| Dialog ARIA | B1.5a | All six panels `role="dialog"` + `aria-modal` + `aria-labelledby` | VERIFIED components; **no `tabIndex={-1}`** on roots (grep empty) |

**Components / partials likely to change (TARGET):**
- `App.tsx` shell structure (rail + panes)
- New CSS (e.g. `desktop.css` or `shell.css` `@media (min-width: 1280px)` only)
- `AskPanel` / overlay CSS: docked mode vs modal (`overlays.css`)
- Possibly `MobileDock` unchanged ≤768

**Must NOT change (mobile rules):**
- `mobile.css` `@media (max-width: 768px)` block and dock `!important` (`mobile.css:1-9`)
- 375 baselines / `MAX_DIFF_PIXELS` entries unless owner-approved
- U4 pixel work / contrast ODs

**Breakpoint conflict:** audit floated optional 1024–1279 2-pane; **D-026 U2** locks tablet as single column through 1279. Prefer **D-026** over older audit optional tier unless owner re-opens. VERIFIED D-026 vs audit §6:274-281 mismatch → owner decision.

---

### B3. Mockup-first (D-026 U8)

Add **new** numbered HTML under `frontend/design-reference/` (keep existing 01–10 as historical mobile/card refs; don’t overwrite without owner call). Suggested:

| File | Must show |
|------|-----------|
| `11-desktop-shell-dashboard.html` | ≥1280 frame: **icon nav rail** (Dashboard, Items, Insights, Briefing, Connections, Settings — order TBD) + center greeting/tiles + **Ask docked right** (~360–400px) with empty state |
| `12-desktop-items-split.html` | Rail + urgency list + **item detail** pane + docked Ask (audit All Items wireframe) |
| `13-desktop-ask-populated.html` | Same shell; Ask column with fixture messages + input/send |
| `14-desktop-briefing.html` | Rail + briefing content + docked Ask |
| `15-desktop-insights.html` | Rail + insights + docked Ask |
| `16-desktop-settings-rail.html` | Settings selected in rail; content = settings form; Ask docked or collapsed per owner |

**Owner review process (STOP before layout code):**
1. Open HTMLs in browser at ~1280 width.
2. Confirm rail items/order, Ask width, Items split vs overlay-first, whether Notify stays dropdown.
3. Written approval quote in PR / PART (same bar as C-BASE gallery).
4. Only then Agent implements CSS/React.

---

### B4. Test plan for B1.5b

| Layer | Plan |
|-------|------|
| Visual 1280 | New states: `desktop-dashboard`, `desktop-ask-docked`, `desktop-items-detail`, rail-selected variants; update existing 1280 baselines that change chrome |
| Visual tablet (~768–1279) | Keep single-column; prove **0** unintended change at 768; optional new 1024 project only if owner wants |
| Visual 375 | **Pixel-identical**; global `maxDiffPixels: 0`; `MAX_DIFF_PIXELS` table **unchanged** unless owner approves |
| Baseline production | UI Baselines workflow only; gallery vs before; attribution; owner approve (D-026 U9 / runbook) |
| e2e | Docked Ask open-by-default ≥1280; Ctrl/Cmd+K focuses dock input; Esc does **not** destroy dock (or only clears nested overlays — owner decide); rail keyboard nav + focus order |
| axe | Routes + docked Ask + rail; keep `color-contrast` disabled per OD-6 until owner |

---

### B5. B1.5a follow-ups (NB-*) vs code

*IDs from the B1.5a final audit request; not present as strings in repo (grep empty). Mapped to CURRENT code:*

| ID | Meaning | Code today | In B1.5b? |
|----|---------|------------|-----------|
| **NB-OV-1** | Shift+Tab / empty trap e2e | Trap implements Shift+Tab + empty (`useOverlay.ts:98-117`); e2e only forward Tab (`overlay-stack.spec.ts:48-66`) | **Yes** — extend e2e; critical when Ask docks |
| **NB-OV-2** | Return focus if opener unmounts | Only restores if `document.contains(previouslyFocused)` (`useOverlay.ts:124-126`) | **Yes if** docked Ask remounts/unmounts openers; else small fix anytime |
| **NB-OV-3** | Dialog roots `tabIndex={-1}` | **Absent** on all panel components (grep no `tabIndex`) | **Yes** — a11y for empty focus target |
| **NB-OV-4** | ARIA e2e all six panels | Only priorities + evening sampled (`overlay-stack.spec.ts:87-101`) | **Yes** — Notify, Ask, Week, Voice too |
| **NB-FX-1** | production-effects gaps | Covers Ask/Week/Priorities/Evening/Notify/halo; **not** `.voice-overlay` / `.onboarding-overlay` backdrop-filter (`mobile.css:52-87`) | **Optional early** (0-pixel) — good before layout |
| **NB-MOBILE-BLUR** | mobile dock backdrop-filter assert | `.mobile-dock` uses solid `#141413`, **no** backdrop-filter; blur is on voice/onboarding overlays | Clarify target: likely **voice overlay** or misnamed; add assertion without touching 375 pixels if computed-style only |

---

### B6. Risks

| Risk | Detail | Mitigation |
|------|--------|------------|
| Nested max-widths | `.content-shell` 1100 + `.dashboard-redesign` 600 | Desktop media queries override only ≥1280; leave ≤1279 alone |
| Dock `!important` | `.mobile-dock { display: flex !important }` (`mobile.css:9`) | Never reuse `.mobile-dock` for desktop Ask; new `.ask-dock` class |
| Ask docked vs modal | `useOverlay` assumes modal open/close | Docked Ask may stay mounted; Escape/stack semantics need explicit design |
| 375 baseline policy | Any 375 PNG change needs owner approval | Gate layout CSS with `min-width: 1280px` only; CI proves 375 0-diff |
| Playwright bump mid-batch | Chromium churn vs new desktop baselines | Finish dep Playwright 1.55.1 **before** B1.5b mocks land |

---

### B7. B1.5b scope proposal

**In:**
- Static desktop mockups + owner STOP
- ≥1280 three-pane (rail + content + docked Ask) per D-026
- Tablet remains single column (769–1279)
- Phone ≤768 untouched
- New/updated 1280 visual baselines via U9 gallery
- e2e/axe for rail + docked Ask
- Fold NB-OV-1/3/4 (and OV-2 if needed); optional NB-FX-1

**Out:**
- Agent Ask SSE / HITL (B5)
- Contrast/focus-ring OD pixels
- Vitest 5 / Playwright 1.63
- Changing 375 baselines without owner
- Optional audit 1024 2-pane unless owner reopens U2

**Commit outline:**
1. Docs/plan ADR note if any U2 clarification  
2. Mockups 11–16 only → **STOP / owner approve**  
3. Desktop shell CSS + App structure (Ask still modal) — prove 375/768 0-diff  
4. Dock Ask ≥1280 + overlay behavior  
5. Rail nav + Settings-in-rail  
6. Items split (if mocked)  
7. e2e/axe/NB-OV\*  
8. UI Baselines refresh + gallery + docs PART  

**Exit criteria:**
- Owner-approved mockups cited in PART  
- UI Tests green; 375 diffs within existing tols (ideally 0 on unchanged states)  
- 1280 shows three-pane in named states  
- Live smoke: exact local/docker e2e commands from runbook  
- ROADMAP B1.5b status + CHANGELOG + PART append after merge  

---

## 3. Owner decisions list

1. **Playwright:** 1.55.1 now (+ likely U9) vs defer all Playwright until after B1.5b (alert remains open).  
2. **Accept or reject Dependabot #19 (1.63.0)** — recommend reject/supersede.  
3. **Vitest 5 (#10):** defer?  
4. **React 19.3 (#11)** now vs after B1.5b; require matching `react-dom`?  
5. **GHA majors #3–#5** now vs later.  
6. **B1.5b rail items and order** (audit list vs Settings placement).  
7. **Docked Ask width** (~360–400?) and always-on vs open-on-demand ≥1280.  
8. **All Items:** list|detail split vs keep priorities overlay initially.  
9. **Tablet:** strict single column through 1279 (D-026) vs audit’s optional 1024 2-pane.  
10. **NB-MOBILE-BLUR** target clarification (dock vs voice overlay).  
11. **Mockup numbering:** new 11+ files vs replace `01-dashboard-desktop.html`.

---

## 4. After You Finish

### 1. Files changed

| Path | Change |
|------|--------|
| — | **None (Ask mode)** |

### 2. Command output summaries (read-only)

- `git`: `main` @ `d1c57e0`; dirty only untracked `scripts/visual_*.py`, `tmp/`  
- `gh pr list`: open #3–#17, #19 (no #18 — merged)  
- `gh api dependabot/alerts`: 10 open npm development alerts (#1–#4, #7, #10, #12–#15)  
- `gh pr view/diff`: version deltas and SHA pins for #3–#5, #9–#11, #13–#17, #19  
- Playwright release notes: Chromium revisions for 1.55.0 / 1.55.1 / 1.63.0  
- Read ADRs D-026/024/027, ROADMAP B1.5b, PART 4, ui-audit §6, CSS, App, useOverlay, e2e, baselines PNGs (dashboard 375/768/1280, ask-empty 1280, items 1280)

### 3. Git log/status

- Branch: `main` tracking `origin/main`  
- HEAD: `d1c57e0 Merge pull request #18 from Settar-Mengli/b1.5a/ui-safety-net`  
- Clean tracked tree; untracked local diagnose scripts + `tmp/`

### 4. Push confirmation

**N/A — read-only.**

### 5. Warnings / concerns

- **#19 is not a security-minimal bump** — it is a Chromium generation jump disguised as a Dependabot “fix.”  
- **1.55.1 still changes Chromium build** — do not assume 0 screenshot drift.  
- **design-reference/01 is not a three-pane mock** — B1.5b mockup-first is still incomplete.  
- **768 still shows mobile dock** while 1280 does not — desktop Ask must be a new surface, not a reused dock.  
- Untracked `tmp/` / diagnose scripts on disk are noise; keep out of dependency/B1.5b commits.
