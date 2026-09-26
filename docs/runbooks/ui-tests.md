# UI Tests (Playwright)

**Authority:** CI Linux using the official Playwright Docker image (pinned to match `@playwright/test`).
Screenshot baselines use Playwright’s platform suffix **`-linux`**.

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

Then commit the updated `*-linux.png` files. The commit message **must name** every changed visual state.

## Fonts

Tests intercept Google Fonts and serve committed WOFF2 files under `frontend/e2e/fixtures/fonts/` (exact files Google serves for the weights in `index.css`, plus `OFL.txt`).

## Determinism

- `/api/v1/**` mocked via Playwright route fixtures
- Frozen clock
- Animations disabled; focus blurred before screenshots
- Visual screenshots force **monospace** via `settle()` so Docker Desktop (Windows) and GHA Linux share `-linux` baselines (production Google Fonts `@import` unchanged)
- localStorage seeded per test
- `deviceScaleFactor: 1`
- `reuseExistingServer: false` (always rebuild preview for screenshots)
