# UI Tests (Playwright)

**Authority:** CI Linux using the official Playwright Docker image (pinned to match `@playwright/test`).
Screenshot baselines use Playwright’s platform suffix **`-linux`**.

## GHA baseline workflow (B1.5a)

Authoritative screenshots are produced only by [`.github/workflows/ui-baselines.yml`](../../.github/workflows/ui-baselines.yml) on GitHub Actions (`mcr.microsoft.com/playwright:v1.55.0-jammy`).

Drive runs by pushing throwaway `visual/**` branches that commit `.github/visual-run.json` (`mode`, `frontend_ref`, `harness_ref`, `artifact_name`; compare also needs `before_artifact_run_id` / `before_artifact_name`), or `workflow_dispatch` with the same fields.

Helper: [`scripts/visual_gallery.mjs`](../../scripts/visual_gallery.mjs) builds the markdown gallery index, enforces the render gate, and compares PNG trees for the E0 determinism gate. Download with `gh run download <run_id> -n <artifact_name>`.

## Unsupported on Windows host

Visual regression (`toHaveScreenshot` / `--update-snapshots`) on the Windows host is **unsupported**.
Do not commit host-generated PNG baselines. Host runs may execute **e2e + axe only** (no screenshot asserts) for quick debugging.

## Local (Windows) — same image as CI

```powershell
$PIN = "v1.55.0-jammy"   # must match @playwright/test major.minor.patch
docker pull mcr.microsoft.com/playwright:$PIN
docker run --rm -it `
  -v ${PWD}:/work `
  -v opspilot-pw-node:/work/frontend/node_modules `
  -w /work/frontend `
  mcr.microsoft.com/playwright:$PIN `
  bash -lc "npm ci && npx playwright test"
```

Update baselines (container only):

```powershell
docker run --rm -it `
  -v ${PWD}:/work `
  -v opspilot-pw-node:/work/frontend/node_modules `
  -w /work/frontend `
  mcr.microsoft.com/playwright:$PIN `
  bash -lc "npm ci && npx playwright test --update-snapshots"
```

Then commit the updated `*-linux.png` files. The commit message **must name** every changed visual state. Any **375** baseline change also needs owner approval in the PR.

## Fonts

Tests intercept Google Fonts and serve committed WOFF2 files under `frontend/e2e/fixtures/fonts/` (exact files Google serves for the weights in `tokens.css`, plus `OFL.txt`). Production `@import` is unchanged. Screenshot settle **does not** substitute monospace or other design fonts.

## Determinism (settle + Chromium)

- `/api/v1/**` mocked via Playwright route fixtures
- Frozen clock for greetings: `page.clock.setFixedTime(2026-09-26T02:00:00.000Z)` in `preparePage` (`frontend/e2e/helpers.ts`); `timezoneId: 'UTC'` (+ `process.env.TZ = 'UTC'`) in `playwright.config.ts`; `settle()` asserts local hour is night (`< 5` or `≥ 22`) so a drifted clock fails loud. **Why night:** approved C-BASE `-linux` baselines show the night greeting ("Working late"); screenshots therefore cover only that greeting variant — not morning/afternoon/evening.
- `settle()` before screenshots: disables **animation / transition / caret**, **`backdrop-filter`**, **`box-shadow` / `filter` / `text-shadow`**, hides scrollbars, asserts Poppins/Lora faces loaded, forces `svg { shape-rendering: crispEdges }`
- **Why exclusions:** Cross-runner Skia noise was measured at up to **72px** with launch-args alone (runs **36292157325 / 36292164473**), dominated by backdrop-blur of header chrome. After settle hardening, residual **shape-edge AA** ≤ **25px** on listed states (pairs **36293955065 / 36293962130**, **36294414647 / 36294419505**).
- **Production still has the effects.** `frontend/e2e/production-effects.spec.ts` asserts computed styles (no `settle()`) on `.ask-panel-overlay`, `.slide-panel-backdrop`, `.evening-panel`, `.notify-panel`, `.bulbul-avatar__halo`. Removing those CSS effects fails the suite.
- Chromium launch args: `--disable-skia-runtime-opts`, `--font-render-hinting=none`, `--disable-font-subpixel-positioning`, `--disable-lcd-text`, `--force-color-profile=srgb`, `--disable-gpu`; `deviceScaleFactor: 1`; `workers: 1`
- `reuseExistingServer: false` (always rebuild preview for screenshots)

## Per-state `maxDiffPixels`

Global default in `playwright.config.ts` is **`maxDiffPixels: 0`**. Owner-approved exceptions live in **one table** in `frontend/e2e/visual.spec.ts` (`MAX_DIFF_PIXELS`). Changing any entry requires **owner approval**.

| State × viewport | Measured noise (px) | Tol |
|------------------|---------------------|-----|
| insights × 375 | 25 | 26 |
| connections-modal × 375 | 18 | 19 |
| notify-open × 375 | 10 | 11 |
| ask-empty × 768 | 8 | 9 |
| week-open × 768 | 8 | 9 |
| evening-error × 1280 | 4 | 5 |
| notify-open × 768 | 4 | 5 |
| all others | 0 | 0 |

Noise source runs: pair4 **36293955065 / 36293962130**, pair5 **36294414647 / 36294419505**.

Mutation proof (must stay ≫ 3× largest tol 26):

| Mutation | Run id | maxDiffPx vs clean |
|----------|--------|--------------------|
| `.nav-gear` color only | **36294854406** | 146 |
| `.top-nav` 1px border-color | **36294859777** | 1280 |
