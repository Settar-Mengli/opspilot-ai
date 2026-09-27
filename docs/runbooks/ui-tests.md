# UI Tests (Playwright)

**Authority:** CI Linux using the official Playwright Docker image (pinned to match `@playwright/test`).
Screenshot baselines use Playwright’s platform suffix **`-linux`**.

## GHA baseline workflow (B1.5a fix pass)

Authoritative screenshots are produced only by [`.github/workflows/ui-baselines.yml`](../../.github/workflows/ui-baselines.yml) on GitHub Actions (`mcr.microsoft.com/playwright:v1.55.0-jammy`).

Until that workflow exists on `main`, drive runs by pushing throwaway `visual/**` branches that commit `.github/visual-run.json` (`mode`, `frontend_ref`, `harness_ref`, `artifact_name`; compare also needs `before_artifact_run_id` / `before_artifact_name`). After merge, prefer `workflow_dispatch` with the same fields.

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

Then commit the updated `*-linux.png` files. The commit message **must name** every changed visual state.

## Fonts

Tests intercept Google Fonts and serve committed WOFF2 files under `frontend/e2e/fixtures/fonts/` (exact files Google serves for the weights in `index.css`, plus `OFL.txt`).

## Determinism

- `/api/v1/**` mocked via Playwright route fixtures
- Frozen clock
- Animations disabled; focus blurred before screenshots
- Visual screenshots force **monospace** via `settle()` so Docker Desktop (Windows) and GHA Linux share `-linux` baselines (production Google Fonts `@import` unchanged)
- If a state still AA-differs (seen on **briefing** prose), **adopt CI `*-actual.png`** as the `-linux` baseline — GHA is authority (D-026)
- localStorage seeded per test
- `deviceScaleFactor: 1`
- `reuseExistingServer: false` (always rebuild preview for screenshots)
