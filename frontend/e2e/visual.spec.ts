import { test, expect } from '@playwright/test'
import { preparePage, settle } from './helpers'

/**
 * Per-state×viewport maxDiffPixels (global default remains 0 in playwright.config).
 * Changing any entry requires owner approval.
 *
 * Noise measured on visual/harness-r1 @ 2bf83f7 (settle: blur/shadow/filter off + crisp SVG):
 *   pair4 a/b: 36293955065 / 36293962130
 *   pair5 a/b: 36294414647 / 36294419505
 * Convention: measured max N → tol N+1 (see D-026 / docs/runbooks/ui-tests.md).
 *
 * B6 new-state AA (update runs 37162007920 vs 37199718443): measured max 27 px,
 * confined to .mic-btn edge AA @375 (bbox 337,750–374,791) and top-nav icon AA @768/1280
 * → tol 28. Do not raise settle()/masks (would churn 62 pre-B6 baselines).
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
  // B6 new states — measured max 27 → tol 28 (mic @375 / top-nav @768|1280)
  'connections-connected-idle-chromium-375': 28,
  'connections-connected-idle-chromium-768': 28,
  'connections-connected-idle-chromium-1280': 28,
  'connections-sync-progress-chromium-375': 28,
  'connections-sync-progress-chromium-768': 28,
  'connections-sync-progress-chromium-1280': 28,
  'connections-sync-triaging-chromium-375': 28,
  'connections-sync-triaging-chromium-768': 28,
  'connections-sync-triaging-chromium-1280': 28,
  'connections-sync-done-chromium-375': 28,
  'connections-sync-done-chromium-768': 28,
  'connections-sync-done-chromium-1280': 28,
  'connections-sync-busy-chromium-375': 28,
  'connections-sync-busy-chromium-768': 28,
  'connections-sync-busy-chromium-1280': 28,
  'settings-job-status-chromium-375': 28,
  'settings-job-status-chromium-768': 28,
  'settings-job-status-chromium-1280': 28,
  'items-correction-controls-chromium-375': 28,
  'items-correction-controls-chromium-768': 28,
  'items-correction-controls-chromium-1280': 28,
  'items-correction-saved-chromium-375': 28,
  'items-correction-saved-chromium-768': 28,
  'items-correction-saved-chromium-1280': 28,
  'ask-draft-failed-reopen-chromium-375': 28,
  'ask-draft-failed-reopen-chromium-768': 28,
  'ask-draft-failed-reopen-chromium-1280': 28,
}

function screenshotOpts(basename: string): { maxDiffPixels: number } {
  const key = `${basename}-${test.info().project.name}`
  return { maxDiffPixels: MAX_DIFF_PIXELS[key] ?? 0 }
}

test.describe('visual baselines', () => {
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
      page.locator('.ask-panel:visible, .desk-ask:visible').getByText(/Ask failed \(ask_failed; ref e2e\)/i),
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

/* ─── B6 connected / job-status / correction / draft-failed visual states ─── */
test.describe('B6 visual states', () => {
  test('connections-connected-idle', async ({ page }) => {
    await preparePage(page, { mode: 'connected' })
    await page.goto('/connections')
    await settle(page)
    await expect(page.locator('.cn-badge', { hasText: 'Connected' }).first()).toBeVisible()
    await expect(page.getByRole('button', { name: /sync now/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /disconnect/i })).toBeVisible()
    await expect(page.getByTestId('sync-status')).toHaveCount(0)
    await expect(page).toHaveScreenshot('connections-connected-idle.png', screenshotOpts('connections-connected-idle'))
  })

  test('connections-sync-progress', async ({ page }) => {
    await preparePage(page, { mode: 'sync-progress' })
    await page.goto('/connections')
    await settle(page)
    await page.getByRole('button', { name: /sync now/i }).click()
    await expect(page.getByRole('button', { name: /syncing/i })).toBeVisible()
    await expect(page.getByTestId('sync-status')).toHaveCount(0)
    await settle(page)
    await expect(page).toHaveScreenshot('connections-sync-progress.png', screenshotOpts('connections-sync-progress'))
  })

  test('connections-sync-triaging', async ({ page }) => {
    await preparePage(page, { mode: 'sync-triaging' })
    await page.goto('/connections')
    await settle(page)
    await page.getByRole('button', { name: /sync now/i }).click()
    await expect(page.getByTestId('sync-status')).toHaveAttribute('data-sync-outcome', 'triaging')
    await expect(page.getByText(/triaging 5 pending/i)).toBeVisible()
    await settle(page)
    await expect(page).toHaveScreenshot('connections-sync-triaging.png', screenshotOpts('connections-sync-triaging'))
  })

  test('connections-sync-done', async ({ page }) => {
    await preparePage(page, { mode: 'sync-done' })
    await page.goto('/connections')
    await settle(page)
    await page.getByRole('button', { name: /sync now/i }).click()
    await expect(page.getByTestId('sync-status')).toHaveAttribute('data-sync-outcome', 'triaging')
    await page.clock.fastForward(2100)
    await expect(page.getByTestId('sync-status')).toHaveAttribute('data-sync-outcome', 'done', {
      timeout: 10_000,
    })
    await expect(page.getByText(/triaged 4 \(1 pending\)/i)).toBeVisible()
    await expect(page.getByRole('button', { name: /sync now/i })).toBeVisible()
    await settle(page)
    await expect(page).toHaveScreenshot('connections-sync-done.png', screenshotOpts('connections-sync-done'))
  })

  test('connections-sync-busy', async ({ page }) => {
    await preparePage(page, { mode: 'sync-busy' })
    await page.goto('/connections')
    await settle(page)
    await page.getByRole('button', { name: /sync now/i }).click()
    await expect(page.getByTestId('sync-status')).toHaveAttribute('data-sync-outcome', 'busy')
    await expect(page.getByText(/triage busy/i)).toBeVisible()
    await expect(page.getByRole('button', { name: /sync now/i })).toBeVisible()
    await settle(page)
    await expect(page).toHaveScreenshot('connections-sync-busy.png', screenshotOpts('connections-sync-busy'))
  })

  test('settings-job-status', async ({ page }) => {
    await preparePage(page, { mode: 'job-status' })
    await page.goto('/settings')
    await settle(page)
    await expect(page.getByText('Last morning run')).toBeVisible()
    await expect(page.getByText('Last sync')).toBeVisible()
    const morning = page.getByTestId('job-block-last-morning-run')
    // Scroll job block into view so Pending / Rules fallback / Re-auth / Finished are on-screen.
    await morning.evaluate((el) => el.scrollIntoView({ block: 'center', inline: 'nearest' }))
    await settle(page)
    await expect(morning.getByText('Pending')).toBeInViewport()
    await expect(morning.getByText('Rules fallback')).toBeInViewport()
    await expect(morning.getByText('Re-auth')).toBeInViewport()
    await expect(morning.getByText('Finished')).toBeInViewport()
    if (test.info().project.name === 'chromium-375') {
      const finished = morning.locator('.settings-status-row', { hasText: 'Finished' })
      const dock = page.locator('.mobile-dock')
      const fBox = await finished.boundingBox()
      const dBox = await dock.boundingBox()
      expect(fBox, 'Finished row bbox').toBeTruthy()
      expect(dBox, 'mobile-dock bbox').toBeTruthy()
      // Product clearance: last job row must sit above the fixed Ask bar (110px content-shell pad).
      expect((fBox!.y + fBox!.height)).toBeLessThanOrEqual(dBox!.y)
    }
    await expect(page).toHaveScreenshot('settings-job-status.png', screenshotOpts('settings-job-status'))
  })

  test('items-correction-controls', async ({ page }) => {
    await preparePage(page, { mode: 'correction' })
    await page.goto('/items')
    await settle(page)
    const row = page.locator('.fp-row').first()
    await row.click()
    await settle(page)
    await expect(page.getByTestId('correction-controls')).toBeVisible()
    await expect(page.getByTestId('correction-badge')).toHaveCount(0)
    await expect(page).toHaveScreenshot('items-correction-controls.png', screenshotOpts('items-correction-controls'))
  })

  test('items-correction-saved', async ({ page }) => {
    await preparePage(page, { mode: 'correction' })
    await page.goto('/items')
    await settle(page)
    const row = page.locator('.fp-row').first()
    await row.click()
    await settle(page)
    const controls = page.getByTestId('correction-controls')
    await controls.locator('select').first().selectOption('medium')
    await controls.getByRole('button', { name: /save correction/i }).click()
    await expect(page.getByTestId('correction-badge').first()).toBeVisible({ timeout: 5_000 })
    // WI-013 moves high→medium; fixture already has one medium → Medium · 2
    await expect(page.getByText(/medium\s*·\s*2/i)).toBeVisible()
    await settle(page)
    await expect(page).toHaveScreenshot('items-correction-saved.png', screenshotOpts('items-correction-saved'))
  })

  test('ask-draft-failed-reopen', async ({ page }) => {
    await preparePage(page, { mode: 'draft-failed' })
    await page.goto('/dashboard')
    await settle(page)
    const isDesktop = test.info().project.name === 'chromium-1280'
    if (!isDesktop) {
      await page.getByRole('button', { name: /just ask me/i }).click()
    }
    const input = isDesktop
      ? page.locator('.desk-ask-input')
      : page.locator('.ask-panel-input:visible').first()
    await expect(input).toBeVisible()
    await input.fill('Draft a reply')
    await (isDesktop
      ? page.locator('.desk-ask .ask-panel-send')
      : page.locator('.ask-panel-send:visible').first()
    ).click()
    const card = page.getByTestId('ask-draft-card')
    await expect(card).toBeVisible({ timeout: 10_000 })
    // Stream must finish (askLoading false) before Approve is usable in practice.
    await expect(page.getByTestId('ask-draft-reopen')).toHaveCount(0)
    const approve = page.getByTestId('ask-draft-approve')
    await expect(approve).toBeVisible()
    await expect(approve).toBeEnabled({ timeout: 15_000 })
    await Promise.all([
      page.waitForResponse(
        (r) => r.url().includes('/mail/drafts/') && r.url().includes('/edit') && r.status() === 200,
        { timeout: 15_000 },
      ),
      approve.click(),
    ])
    await expect(page.getByTestId('ask-draft-reopen')).toBeVisible({ timeout: 15_000 })
    await expect(page.locator('.ask-draft-approve-error')).toBeVisible()
    await expect(approve).toBeEnabled()
    await settle(page)
    await expect(page).toHaveScreenshot('ask-draft-failed-reopen.png', screenshotOpts('ask-draft-failed-reopen'))
  })
})

/** B1.5b desktop chrome states — chromium-1280 only. */
test.describe('desktop visual states ≥1280', () => {
  test.beforeEach(() => {
    test.skip(
      test.info().project.name !== 'chromium-1280',
      'desktop visual states are chromium-1280 only',
    )
  })

  test('items-split', async ({ page }) => {
    await preparePage(page)
    await page.goto('/items')
    await settle(page)
    await expect(page.locator('.items-split')).toBeVisible()
    await expect(page.locator('.fp-row.is-selected')).toBeVisible()
    await expect(page).toHaveScreenshot('items-split.png', screenshotOpts('items-split'))
  })

  test('ask-docked-empty', async ({ page }) => {
    await preparePage(page)
    await page.goto('/dashboard')
    await settle(page)
    await expect(page.locator('.desk-ask-input')).toBeVisible()
    await expect(page).toHaveScreenshot('ask-docked-empty.png', screenshotOpts('ask-docked-empty'))
  })

  test('ask-docked-messages', async ({ page }) => {
    await preparePage(page)
    await page.goto('/dashboard')
    await settle(page)
    const input = page.locator('.desk-ask-input')
    await input.fill('What needs attention?')
    await page.locator('.desk-ask .ask-panel-send').click()
    await expect(page.locator('.desk-ask').getByText(/Checkout confirm is the priority/i)).toBeVisible()
    await settle(page)
    await expect(page).toHaveScreenshot('ask-docked-messages.png', screenshotOpts('ask-docked-messages'))
  })

  test('settings-rail-active', async ({ page }) => {
    await preparePage(page)
    await page.goto('/settings')
    await settle(page)
    await expect(
      page.getByRole('navigation', { name: 'Primary' }).getByRole('link', { name: 'Settings' }),
    ).toHaveAttribute('aria-current', 'page')
    await expect(page).toHaveScreenshot('settings-rail-active.png', screenshotOpts('settings-rail-active'))
  })

  test('overlays-over-layout', async ({ page }) => {
    await preparePage(page)
    await page.goto('/dashboard')
    await settle(page)
    await page.locator('.dash-hero').click()
    await expect(page.locator('.slide-panel').first()).toBeVisible()
    await expect(page.locator('aside.desk-ask')).toBeVisible()
    await settle(page)
    await expect(page).toHaveScreenshot('overlays-over-layout.png', screenshotOpts('overlays-over-layout'))
  })

  test('items-split-correction', async ({ page }) => {
    await preparePage(page, { mode: 'correction' })
    await page.goto('/items')
    await settle(page)
    await expect(page.locator('.items-split')).toBeVisible()
    await expect(page.getByTestId('correction-controls')).toBeVisible()
    await expect(page).toHaveScreenshot('items-split-correction.png', screenshotOpts('items-split-correction'))
  })
})
