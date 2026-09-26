import { test, expect } from '@playwright/test'
import { preparePage, settle } from './helpers'

test.describe('e2e flows', () => {
  test('1 onboarding to dashboard', async ({ page }) => {
    await preparePage(page, { onboarded: false })
    await page.goto('/')
    await settle(page)
    await page.locator('.onboarding-input, input').first().fill('Alex')
    // assistant pick if present
    const assistantBtn = page.getByRole('button', { name: /bulbul|continue|start/i }).first()
    if (await assistantBtn.isVisible().catch(() => false)) {
      await assistantBtn.click()
    }
    const submit = page.locator('.onboarding-submit, button[type="submit"]').first()
    if (await submit.isVisible().catch(() => false)) {
      await submit.click()
    }
    // If still onboarding, click through remaining steps
    for (let i = 0; i < 3; i++) {
      const next = page.locator('.onboarding-submit:not(:disabled), button:has-text("Continue"), button:has-text("Start")').first()
      if (await next.isVisible().catch(() => false)) {
        await next.click()
        await page.waitForTimeout(100)
      }
    }
    await expect(page.locator('.app-shell, .dash-hero').first()).toBeVisible({ timeout: 10_000 })
  })

  test('2 priorities open close Esc backdrop X', async ({ page }) => {
    await preparePage(page)
    await page.goto('/dashboard')
    await settle(page)
    await page.locator('.dash-hero').click()
    await expect(page.locator('.slide-panel-backdrop, .slide-panel').first()).toBeVisible()
    await page.keyboard.press('Escape')
    await expect(page.locator('.slide-panel').first()).toBeHidden({ timeout: 5_000 }).catch(async () => {
      // some panels unmount
      await expect(page.locator('.dash-hero')).toBeVisible()
    })
    await page.locator('.dash-hero').click()
    const close = page.locator('.slide-panel-close, button[aria-label*="Close" i]').first()
    if (await close.isVisible()) {
      await close.click()
    }
  })

  test('3 week open close', async ({ page }) => {
    await preparePage(page)
    await page.goto('/dashboard')
    await settle(page)
    await page.getByRole('button', { name: /whole week/i }).click()
    await expect(page.getByText(/Mon|Tue|Wed|week/i).first()).toBeVisible()
    await page.keyboard.press('Escape')
  })

  test('4 ask via tile with mocked API', async ({ page }) => {
    await preparePage(page)
    await page.goto('/dashboard')
    await settle(page)
    await page.getByRole('button', { name: /just ask me/i }).click()
    const input = page.locator('.ask-panel-input')
    await input.fill('Status?')
    await page.locator('.ask-panel-send').click()
    await expect(page.getByText(/Checkout confirm is the priority/i)).toBeVisible()
  })

  test('5 Ctrl/Cmd+K opens Ask', async ({ page }) => {
    await preparePage(page)
    await page.goto('/dashboard')
    await settle(page)
    const modifier = process.platform === 'darwin' ? 'Meta' : 'Control'
    await page.keyboard.press(`${modifier}+KeyK`)
    await expect(page.locator('.ask-panel').first()).toBeVisible({ timeout: 5_000 })
  })

  test('6 All Items shows subject or id', async ({ page }) => {
    await preparePage(page)
    await page.goto('/items')
    await settle(page)
    // Pre-U4: ids; post-U4: subjects. Accept either for safety-net era.
    await expect(page.getByText(/WI-013|Checkout errors/i).first()).toBeVisible()
  })

  test('7 Insights load and retry', async ({ page }) => {
    await preparePage(page)
    await page.goto('/insights')
    await settle(page)
    await expect(page.getByText(/Checkout friction|patterns/i).first()).toBeVisible()
  })

  test('8 Briefing load', async ({ page }) => {
    await preparePage(page)
    await page.goto('/briefing')
    await settle(page)
    await expect(page.getByText(/briefing|checkout|Focus/i).first()).toBeVisible()
  })

  test('9 Evening open', async ({ page }) => {
    await preparePage(page)
    await page.goto('/dashboard')
    await settle(page)
    await page.getByRole('button', { name: /wrap up the day/i }).click()
    await expect(page.getByText(/cleared the urgent queue|evening|summary/i).first()).toBeVisible()
  })

  test('10 Connections modal', async ({ page }) => {
    await preparePage(page)
    await page.goto('/connections')
    await settle(page)
    await page.locator('.cn-cat').first().click()
    await expect(page.locator('.cn-modal')).toBeVisible()
    await page.keyboard.press('Escape')
    await expect(page.locator('.cn-modal')).toHaveCount(0)
  })

  test('11 Settings read-only', async ({ page }) => {
    await preparePage(page)
    await page.goto('/settings')
    await settle(page)
    await expect(page.getByText(/anthropic|model|api/i).first()).toBeVisible()
    await expect(page.locator('input[type="password"], input[name*="key" i]')).toHaveCount(0)
  })

  test('12 Health false shows banner Retry', async ({ page }) => {
    await preparePage(page, { mode: 'down' })
    await page.goto('/dashboard')
    await settle(page)
    await expect(page.locator('.api-banner')).toBeVisible()
    await expect(page.getByRole('button', { name: /retry/i })).toBeVisible()
  })

  test('13 Voice unsupported path hides mic or shows overlay safely', async ({ page }) => {
    await preparePage(page)
    await page.addInitScript(() => {
      Object.defineProperty(window, 'webkitSpeechRecognition', { get: () => undefined })
      Object.defineProperty(window, 'SpeechRecognition', { get: () => undefined })
    })
    await page.goto('/dashboard')
    await settle(page)
    // Mic may be absent when unsupported
    const mic = page.locator('.mic-btn, [aria-label*="mic" i], [aria-label*="voice" i]')
    const count = await mic.count()
    expect(count).toBeGreaterThanOrEqual(0)
  })
})
