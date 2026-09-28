import { test, expect } from '@playwright/test'
import { preparePage, settle } from './helpers'

/**
 * Per-state×viewport maxDiffPixels (global default remains 0 in playwright.config).
 * Changing any entry requires owner approval.
 *
 * Noise measured on visual/harness-r1 @ 2bf83f7 (settle: blur/shadow/filter off + crisp SVG):
 *   pair4 a/b: 36293955065 / 36293962130
 *   pair5 a/b: 36294414647 / 36294419505
 * Keys = `{screenshotBasename}-{projectName}` (no .png).
 */
const MAX_DIFF_PIXELS: Record<string, number> = {
  // measured max 25 → tol 26
  'insights-chromium-375': 26,
  // measured max 18 → tol 19
  'connections-modal-chromium-375': 19,
  // measured max 10 → tol 11
  'notify-open-chromium-375': 11,
  // measured max 8 → tol 9
  'ask-empty-chromium-768': 9,
  // measured max 8 → tol 9
  'week-open-chromium-768': 9,
  // measured max 4 → tol 5
  'evening-error-chromium-1280': 5,
  // measured max 4 → tol 5
  'notify-open-chromium-768': 5,
}

function screenshotOpts(basename: string): { maxDiffPixels: number } {
  const key = `${basename}-${test.info().project.name}`
  return { maxDiffPixels: MAX_DIFF_PIXELS[key] ?? 0 }
}

/** Temporary B1.5b hold: skip only chromium-1280 screenshot asserts while desktop layout lands. */
function skip1280ScreenshotIfHeld(): void {
  const held = process.env.B15B_DESKTOP_HOLD === '1'
  const is1280 = test.info().project.name === 'chromium-1280'
  test.skip(
    held && is1280,
    'B15B_DESKTOP_HOLD: 1280 screenshots deferred until baseline commit',
  )
}

test.describe('visual baselines', () => {
  test.beforeEach(() => {
    skip1280ScreenshotIfHeld()
  })

  test('onboarding', async ({ page }) => {
    await preparePage(page, { onboarded: false })
    await page.goto('/')
    await settle(page)
    await expect(page).toHaveScreenshot('onboarding.png', screenshotOpts('onboarding'))
  })

  test('dashboard', async ({ page }) => {
    await preparePage(page)
    await page.goto('/dashboard')
    await settle(page)
    await expect(page.locator('.dash-hero')).toBeVisible()
    await expect(page).toHaveScreenshot('dashboard.png', screenshotOpts('dashboard'))
  })

  test('priorities-open', async ({ page }) => {
    await preparePage(page)
    await page.goto('/dashboard')
    await settle(page)
    await page.locator('.dash-hero').click()
    await expect(page.locator('.slide-panel, .priorities-panel, [class*="priorit"]').first()).toBeVisible()
    await settle(page)
    await expect(page).toHaveScreenshot('priorities-open.png', screenshotOpts('priorities-open'))
  })

  test('week-open', async ({ page }) => {
    await preparePage(page)
    await page.goto('/dashboard')
    await settle(page)
    await page.getByRole('button', { name: /whole week/i }).click()
    await settle(page)
    await expect(page).toHaveScreenshot('week-open.png', screenshotOpts('week-open'))
  })

  test('ask-empty', async ({ page }) => {
    await preparePage(page)
    await page.goto('/dashboard')
    await settle(page)
    await page.getByRole('button', { name: /just ask me/i }).click()
    await settle(page)
    await expect(page).toHaveScreenshot('ask-empty.png', screenshotOpts('ask-empty'))
  })

  test('ask-with-messages', async ({ page }) => {
    await preparePage(page)
    await page.goto('/dashboard')
    await settle(page)
    await page.getByRole('button', { name: /just ask me/i }).click()
    const input = page.locator('.ask-panel-input:visible, .desk-ask-input:visible').first()
    await input.fill('What needs attention?')
    await page.locator('.ask-panel-send:visible').first().click()
    await expect(
      page.locator('.ask-panel:visible, .desk-ask:visible').getByText(/Checkout confirm is the priority/i),
    ).toBeVisible()
    await settle(page)
    await expect(page).toHaveScreenshot('ask-with-messages.png', screenshotOpts('ask-with-messages'))
  })

  test('evening-open', async ({ page }) => {
    await preparePage(page)
    await page.goto('/dashboard')
    await settle(page)
    await page.getByRole('button', { name: /wrap up the day/i }).click()
    await expect(page.getByText(/cleared the urgent queue|Nothing else|summary/i).first()).toBeVisible({
      timeout: 10_000,
    })
    await settle(page)
    await expect(page).toHaveScreenshot('evening-open.png', screenshotOpts('evening-open'))
  })

  test('notify-open', async ({ page }) => {
    await preparePage(page)
    await page.goto('/dashboard')
    await settle(page)
    await page.locator('.bell-btn').first().click()
    await settle(page)
    await expect(page).toHaveScreenshot('notify-open.png', screenshotOpts('notify-open'))
  })

  test('items', async ({ page }) => {
    await preparePage(page)
    await page.goto('/items')
    await settle(page)
    await expect(page).toHaveScreenshot('items.png', screenshotOpts('items'))
  })

  test('insights', async ({ page }) => {
    await preparePage(page)
    await page.goto('/insights')
    await settle(page)
    await expect(page.getByText(/Checkout friction|patterns/i).first()).toBeVisible()
    await expect(page).toHaveScreenshot('insights.png', screenshotOpts('insights'))
  })

  test('briefing', async ({ page }) => {
    await preparePage(page)
    await page.goto('/briefing')
    await settle(page)
    await expect(page).toHaveScreenshot('briefing.png', screenshotOpts('briefing'))
  })

  test('connections', async ({ page }) => {
    await preparePage(page)
    await page.goto('/connections')
    await settle(page)
    await expect(page).toHaveScreenshot('connections.png', screenshotOpts('connections'))
  })

  test('connections-modal', async ({ page }) => {
    await preparePage(page)
    await page.goto('/connections')
    await settle(page)
    await page.locator('.cn-cat').first().click()
    await expect(page.locator('.cn-modal')).toBeVisible()
    await settle(page)
    await expect(page).toHaveScreenshot('connections-modal.png', screenshotOpts('connections-modal'))
  })

  test('settings', async ({ page }) => {
    await preparePage(page)
    await page.goto('/settings')
    await settle(page)
    await expect(page).toHaveScreenshot('settings.png', screenshotOpts('settings'))
  })

  test('api-down-banner', async ({ page }) => {
    await preparePage(page, { mode: 'down' })
    await page.goto('/dashboard')
    await settle(page)
    await expect(page.locator('.api-banner')).toBeVisible()
    await expect(page).toHaveScreenshot('api-down-banner.png', screenshotOpts('api-down-banner'))
  })

  test('ask-error', async ({ page }) => {
    await preparePage(page, { mode: 'ask-error' })
    await page.goto('/dashboard')
    await settle(page)
    await page.getByRole('button', { name: /just ask me/i }).click()
    const input = page.locator('.ask-panel-input:visible, .desk-ask-input:visible').first()
    await input.fill('Hello')
    await page.locator('.ask-panel-send:visible').first().click()
    await expect(
      page.locator('.ask-panel:visible, .desk-ask:visible').getByText(/Ask fixture error|500/i),
    ).toBeVisible()
    await settle(page)
    await expect(page).toHaveScreenshot('ask-error.png', screenshotOpts('ask-error'))
  })

  test('insights-error', async ({ page }) => {
    await preparePage(page, { mode: 'insights-error' })
    await page.goto('/insights')
    await settle(page)
    await expect(page.locator('.insights-error')).toBeVisible()
    await expect(page).toHaveScreenshot('insights-error.png', screenshotOpts('insights-error'))
  })

  test('dashboard-error', async ({ page }) => {
    await preparePage(page, { mode: 'triage-error' })
    await page.goto('/dashboard')
    await settle(page)
    await expect(page.locator('.insights-error')).toBeVisible()
    await expect(page).toHaveScreenshot('dashboard-error.png', screenshotOpts('dashboard-error'))
  })

  test('evening-error', async ({ page }) => {
    await preparePage(page, { mode: 'evening-error' })
    await page.goto('/dashboard')
    await settle(page)
    await page.getByRole('button', { name: /wrap up the day/i }).click()
    await expect(page.getByText(/Evening fixture error|Something went wrong/i).first()).toBeVisible({
      timeout: 10_000,
    })
    await settle(page)
    await expect(page).toHaveScreenshot('evening-error.png', screenshotOpts('evening-error'))
  })
})
