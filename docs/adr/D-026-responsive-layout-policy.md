# D-026: Responsive layout policy

- **Date:** 2026-09-26
- **Status:** Accepted
- **Blocks:** B1.5a, B1.5b, B5+

## Context

The Command Center UI must stay calm and predictable across phone, tablet, and desktop while a safety net (Playwright visual/e2e/axe) lands before any desktop layout rebuild. Owner rulings U1–U10 define breakpoints, what may change on mobile, and how baselines are produced.

## Decision

- **U1/U3/U6/U7 (B1.5b):** At ≥1280, three-pane (icon nav rail + content + docked Ask); Settings in rail; gear stays → `/connections` labeled Connections; mobile footer Settings remains.
- **U2:** phone ≤768 pixel-identical to CURRENT at B1.5a start (except owner-approved U4); tablet 769–1279 = single centered column; wide ≥1280 = three-pane (B1.5b).
- **U4/U5:** Mobile visual changes only with owner approval (U4 list + Sample badges until B4 + C16 token aliases). Behavior-only changes OK at 0 screenshot diff.
- **U8:** B1.5a = safety net + hygiene; B1.5b = desktop from approved static mocks in `frontend/design-reference/`.
- **U9:** Screenshot authority is the **GHA pinned Playwright image only**. Local Docker Desktop is **not** pixel-equivalent (measured). Local runs are for e2e/axe and non-authoritative drafts only. Baselines are produced only via the UI Baselines workflow (`visual/*` push before merge, `workflow_dispatch` after merge). Baselines keep `-linux` suffix; never generate visual baselines on the Windows host.
  - **Screenshot settle exclusions (B1.5a fix pass):** Visual `settle()` disables `backdrop-filter`, `box-shadow`, `filter`, `text-shadow`, and forces `svg { shape-rendering: crispEdges }` solely to kill measured cross-runner Skia nondeterminism (E0 pairs **36293955065/36293962130**, **36294414647/36294419505**; pre-fix noise up to 72px from backdrop blur — runs **36292157325/36292164473**). Production CSS keeps those effects; `frontend/e2e/production-effects.spec.ts` asserts computed styles on the exact partial selectors (`.ask-panel-overlay`, `.slide-panel-backdrop`, `.evening-panel`, `.notify-panel`, `.bulbul-avatar__halo`).
  - **Per-state `maxDiffPixels`:** Global default remains **0**. Owner-approved exceptions live only in `frontend/e2e/visual.spec.ts` (`MAX_DIFF_PIXELS`); changing any entry requires owner approval. Measured noise → tol: insights×375 25→26, connections-modal×375 18→19, notify-open×375 10→11, ask-empty×768 8→9, week-open×768 8→9, evening-error×1280 4→5, notify-open×768 4→5.
  - **Mutation proof (tol still catches small chrome regressions):** gear color run **36294854406** (maxDiffPx 146); top-nav 1px border-color run **36294859777** (maxDiffPx 1280). Both ≫ 3× largest tol (26).
- **U10:** `index.css` split in B1.5a after the safety net; proven 0-diff across viewports before overlay migrations.
- **UI workflow:** Any 375 baseline change needs owner approval in PR + visual sign-off. Contrast/focus-ring pixel changes are separate ODs (not auto-applied).

## Consequences

- Visual regressions blocked by container-only `-linux` baselines and the CI **UI Tests** job.
- Desktop three-pane is **out of scope** for B1.5a; B1.5b owns it.
- Host `npx playwright test` may run e2e/axe only; host-generated PNGs are unsupported.
