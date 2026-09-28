import { test, expect } from '@playwright/test'
import { preparePage, settle } from './helpers'

const isDesktopProject = () => test.info().project.name === 'chromium-1280'

test.describe('desktop layout ≥1280', () => {
  test.beforeEach(() => {
    test.skip(!isDesktopProject(), 'desktop layout assertions are chromium-1280 only')
  })

  test('primary rail and docked Ask landmarks', async ({ page }) => {
    await preparePage(page)
    await page.goto('/dashboard')
    await settle(page)

    const rail = page.getByRole('navigation', { name: 'Primary' })
    await expect(rail).toBeVisible()
    await expect(rail.getByRole('link', { name: 'Dashboard' })).toHaveAttribute(
      'aria-current',
      'page',
    )

    await expect(page.locator('aside.desk-ask')).toBeVisible()
    await expect(page.locator('.desk-ask-input')).toBeVisible()
  })

  test('Ctrl/Cmd+K focuses docked Ask input', async ({ page }) => {
    await preparePage(page)
    await page.goto('/dashboard')
    await settle(page)

    const modifier = process.platform === 'darwin' ? 'Meta' : 'Control'
    await page.keyboard.press(`${modifier}+KeyK`)
    await expect(page.locator('.desk-ask-input')).toBeFocused()
  })

  test('Escape closes modal but not docked Ask', async ({ page }) => {
    await preparePage(page)
    await page.goto('/dashboard')
    await settle(page)

    await page.locator('.dash-hero').click()
    await expect(page.locator('.slide-panel').first()).toBeVisible()
    await expect(page.locator('aside.desk-ask')).toBeVisible()

    await page.keyboard.press('Escape')
    await expect(page.locator('.slide-panel')).toHaveCount(0)
    await expect(page.locator('aside.desk-ask')).toBeVisible()
  })

  test('rail navigates with aria-current', async ({ page }) => {
    await preparePage(page)
    await page.goto('/dashboard')
    await settle(page)
    await page.getByRole('navigation', { name: 'Primary' }).getByRole('link', { name: 'Briefing' }).click()
    await settle(page)
    await expect(page).toHaveURL(/\/briefing/)
    await expect(
      page.getByRole('navigation', { name: 'Primary' }).getByRole('link', { name: 'Briefing' }),
    ).toHaveAttribute('aria-current', 'page')
  })

  test('items split shows detail for first urgent', async ({ page }) => {
    await preparePage(page)
    await page.goto('/items')
    await settle(page)
    await expect(page.locator('.items-split')).toBeVisible()
    await expect(page.locator('.items-detail-pane')).toBeVisible()
    await expect(page.locator('.fp-row.is-selected')).toBeVisible()
  })
})

test.describe('docked Ask hidden below 1280', () => {
  test.beforeEach(() => {
    test.skip(isDesktopProject(), 'mobile/tablet only')
  })

  test('rail and docked Ask not in accessibility tree', async ({ page }) => {
    await preparePage(page)
    await page.goto('/dashboard')
    await settle(page)

    await expect(page.getByRole('navigation', { name: 'Primary' })).toHaveCount(0)
    await expect(page.locator('aside.desk-ask')).toHaveCount(0)
  })
})
