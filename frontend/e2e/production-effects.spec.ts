import { test, expect, type Page, type Locator } from '@playwright/test'
import { preparePage } from './helpers'

/**
 * Production computed-style guards for effects that visual settle() disables
 * (backdrop-filter, box-shadow, filter, text-shadow, animations).
 * These tests must NOT call settle() — that injects the harness overrides.
 *
 * Selectors match CSS partials:
 *   overlays.css — .ask-panel-overlay, .evening-panel
 *   dashboard.css — .slide-panel-backdrop (Week + Priorities)
 *   shell.css — .notify-panel
 *   tokens.css — .bulbul-avatar__halo (presence glow)
 *
 * Note: .ask-panel / .slide-panel have no production box-shadow; Ask/Week/Priorities
 * surfaces are covered via their backdrop-filter backdrops above. Evening + Notify
 * panels own box-shadow in CSS.
 */

async function computed(locator: Locator, prop: string): Promise<string> {
  return locator.evaluate((el, p) => getComputedStyle(el).getPropertyValue(p).trim(), prop)
}

async function assertBackdropFilter(page: Page, selector: string): Promise<void> {
  const el = page.locator(selector).first()
  await expect(el).toBeVisible()
  const value = await computed(el, 'backdrop-filter')
  const webkit = await computed(el, '-webkit-backdrop-filter')
  const effective = value !== 'none' && value !== '' ? value : webkit
  expect(effective, `${selector} backdrop-filter`).not.toBe('none')
  expect(effective.length, `${selector} backdrop-filter non-empty`).toBeGreaterThan(0)
}

async function assertBoxShadow(page: Page, selector: string): Promise<void> {
  const el = page.locator(selector).first()
  await expect(el).toBeVisible()
  const value = await computed(el, 'box-shadow')
  expect(value, `${selector} box-shadow`).not.toBe('none')
  expect(value.length, `${selector} box-shadow non-empty`).toBeGreaterThan(0)
}

test.describe('production overlay effects (no settle)', () => {
  test('Ask overlay keeps backdrop-filter (.ask-panel-overlay)', async ({ page }) => {
    test.skip(
      test.info().project.name === 'chromium-1280',
      'Ask is docked at ≥1280; modal overlay not mounted',
    )
    await preparePage(page)
    await page.goto('/dashboard')
    await page.getByRole('button', { name: /just ask me/i }).click()
    await expect(page.locator('.ask-panel')).toBeVisible()
    await assertBackdropFilter(page, '.ask-panel-overlay')
  })

  test('Week / Priorities backdrop keeps backdrop-filter (.slide-panel-backdrop)', async ({
    page,
  }) => {
    await preparePage(page)
    await page.goto('/dashboard')
    await page.getByRole('button', { name: /whole week/i }).click()
    await expect(page.locator('.slide-panel')).toBeVisible()
    await assertBackdropFilter(page, '.slide-panel-backdrop')
  })

  test('Priorities backdrop keeps backdrop-filter (.slide-panel-backdrop)', async ({ page }) => {
    await preparePage(page)
    await page.goto('/dashboard')
    await page.locator('.dash-hero').click()
    await expect(page.locator('.slide-panel')).toBeVisible()
    await assertBackdropFilter(page, '.slide-panel-backdrop')
  })

  test('Evening panel keeps box-shadow (.evening-panel)', async ({ page }) => {
    await preparePage(page)
    await page.goto('/dashboard')
    await page.getByRole('button', { name: /wrap up the day/i }).click()
    await expect(page.locator('.evening-panel-overlay.open')).toBeVisible({ timeout: 10_000 })
    await assertBoxShadow(page, '.evening-panel')
  })

  test('Notify panel keeps box-shadow (.notify-panel)', async ({ page }) => {
    await preparePage(page)
    await page.goto('/dashboard')
    await page.locator('.bell-btn').first().click()
    await expect(page.locator('.notify-panel.open')).toBeVisible()
    await assertBoxShadow(page, '.notify-panel')
  })

  test('Bulbul avatar halo keeps presence glow animation (.bulbul-avatar__halo)', async ({
    page,
  }) => {
    await preparePage(page)
    await page.goto('/dashboard')
    const halo = page.locator('.bulbul-avatar__halo').first()
    await expect(halo).toBeVisible()
    const animation = await computed(halo, 'animation-name')
    expect(animation, '.bulbul-avatar__halo animation-name').not.toBe('none')
    expect(animation.toLowerCase()).toContain('presence-breathe')
  })

  test('Voice overlay keeps backdrop-filter (.voice-overlay)', async ({ page }) => {
    test.skip(
      test.info().project.name === 'chromium-1280',
      'Mic lives in mobile dock (≤768); voice overlay exercised on phone/tablet',
    )
    await preparePage(page)
    await page.goto('/dashboard')
    const mic = page.getByRole('button', { name: /voice input/i })
    await expect(mic).toBeVisible()
    await mic.click()
    await expect(page.locator('.voice-overlay.open')).toBeVisible()
    await assertBackdropFilter(page, '.voice-overlay')
  })

  test('Onboarding overlay keeps backdrop-filter (.onboarding-overlay)', async ({ page }) => {
    await preparePage(page, { onboarded: false })
    await page.goto('/')
    await expect(page.locator('.onboarding-overlay')).toBeVisible()
    await assertBackdropFilter(page, '.onboarding-overlay')
  })
})
