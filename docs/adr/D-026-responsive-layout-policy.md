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
- **U9:** Screenshot authority = CI Linux official Playwright image (pinned). Operator reproduces via the **identical container** on Windows. Baselines keep `-linux` suffix; never generate visual baselines on the Windows host.
- **U10:** `index.css` split in B1.5a after the safety net; proven 0-diff across viewports before overlay migrations.
- **UI workflow:** Any 375 baseline change needs owner approval in PR + visual sign-off. Contrast/focus-ring pixel changes are separate ODs (not auto-applied).

## Consequences

- Visual regressions blocked by container-only `-linux` baselines and the CI **UI Tests** job.
- Desktop three-pane is **out of scope** for B1.5a; B1.5b owns it.
- Host `npx playwright test` may run e2e/axe only; host-generated PNGs are unsupported.
