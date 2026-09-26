import { test, expect } from '@playwright/test'
import { preparePage, settle } from './helpers'

test.describe('visual baselines', () => {
  test('onboarding', async ({ page }) => {
    await preparePage(page, { onboarded: false })
    await page.goto('/')
    await settle(page)
    await expect(page).toHaveScreenshot('onboarding.png')
  })

  test('dashboard', async ({ page }) => {
    await preparePage(page)
    await page.goto('/dashboard')
    await settle(page)
    await expect(page.locator('.dash-hero')).toBeVisible()
    await expect(page).toHaveScreenshot('dashboard.png')
  })

  test('priorities-open', async ({ page }) => {
    await preparePage(page)
    await page.goto('/dashboard')
    await settle(page)
    await page.locator('.dash-hero').click()
    await expect(page.locator('.slide-panel, .priorities-panel, [class*="priorit"]').first()).toBeVisible()
    await settle(page)
    await expect(page).toHaveScreenshot('priorities-open.png')
  })

  test('week-open', async ({ page }) => {
    await preparePage(page)
    await page.goto('/dashboard')
    await settle(page)
    await page.getByRole('button', { name: /whole week/i }).click()
    await settle(page)
    await expect(page).toHaveScreenshot('week-open.png')
  })

  test('ask-empty', async ({ page }) => {
    await preparePage(page)
    await page.goto('/dashboard')
    await settle(page)
    await page.getByRole('button', { name: /just ask me/i }).click()
    await settle(page)
    await expect(page).toHaveScreenshot('ask-empty.png')
  })

  test('ask-with-messages', async ({ page }) => {
    await preparePage(page)
    await page.goto('/dashboard')
    await settle(page)
    await page.getByRole('button', { name: /just ask me/i }).click()
    const input = page.locator('.ask-panel-input')
    await input.fill('What needs attention?')
    await page.locator('.ask-panel-send').click()
    await expect(page.getByText(/Checkout confirm is the priority/i)).toBeVisible()
    await settle(page)
    await expect(page).toHaveScreenshot('ask-with-messages.png')
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
    await expect(page).toHaveScreenshot('evening-open.png')
  })

  test('notify-open', async ({ page }) => {
    await preparePage(page)
    await page.goto('/dashboard')
    await settle(page)
    await page.locator('.bell-btn').first().click()
    await settle(page)
    await expect(page).toHaveScreenshot('notify-open.png')
  })

  test('items', async ({ page }) => {
    await preparePage(page)
    await page.goto('/items')
    await settle(page)
    await expect(page).toHaveScreenshot('items.png')
  })

  test('insights', async ({ page }) => {
    await preparePage(page)
    await page.goto('/insights')
    await settle(page)
    await expect(page.getByText(/Checkout friction|patterns/i).first()).toBeVisible()
    await expect(page).toHaveScreenshot('insights.png')
  })

  test('briefing', async ({ page }) => {
    await preparePage(page)
    await page.goto('/briefing')
    await settle(page)
    await expect(page).toHaveScreenshot('briefing.png')
  })

  test('connections', async ({ page }) => {
    await preparePage(page)
    await page.goto('/connections')
    await settle(page)
    await expect(page).toHaveScreenshot('connections.png')
  })

  test('connections-modal', async ({ page }) => {
    await preparePage(page)
    await page.goto('/connections')
    await settle(page)
    await page.locator('.cn-cat').first().click()
    await expect(page.locator('.cn-modal')).toBeVisible()
    await settle(page)
    await expect(page).toHaveScreenshot('connections-modal.png')
  })

  test('settings', async ({ page }) => {
    await preparePage(page)
    await page.goto('/settings')
    await settle(page)
    await expect(page).toHaveScreenshot('settings.png')
  })

  test('api-down-banner', async ({ page }) => {
    await preparePage(page, { mode: 'down' })
    await page.goto('/dashboard')
    await settle(page)
    await expect(page.locator('.api-banner')).toBeVisible()
    await expect(page).toHaveScreenshot('api-down-banner.png')
  })

  test('ask-error', async ({ page }) => {
    await preparePage(page, { mode: 'ask-error' })
    await page.goto('/dashboard')
    await settle(page)
    await page.getByRole('button', { name: /just ask me/i }).click()
    const input = page.locator('.ask-panel-input')
    await input.fill('Hello')
    await page.locator('.ask-panel-send').click()
    await expect(page.getByText(/Ask fixture error|500/i).first()).toBeVisible()
    await settle(page)
    await expect(page).toHaveScreenshot('ask-error.png')
  })

  test('insights-error', async ({ page }) => {
    await preparePage(page, { mode: 'insights-error' })
    await page.goto('/insights')
    await settle(page)
    await expect(page.locator('.insights-error')).toBeVisible()
    await expect(page).toHaveScreenshot('insights-error.png')
  })

  test('dashboard-error', async ({ page }) => {
    await preparePage(page, { mode: 'triage-error' })
    await page.goto('/dashboard')
    await settle(page)
    await expect(page.locator('.insights-error')).toBeVisible()
    await expect(page).toHaveScreenshot('dashboard-error.png')
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
    await expect(page).toHaveScreenshot('evening-error.png')
  })
})
