import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { preparePage, settle } from './helpers'

const ROUTES = [
  '/dashboard',
  '/items',
  '/insights',
  '/briefing',
  '/connections',
  '/settings',
] as const

// OD-1 / OD-6: color-contrast serious findings are an owner decision (pixel-changing).
// Fail on other serious/critical rules only.
const AXE_DISABLE = ['color-contrast']

async function assertAxe(page: import('@playwright/test').Page): Promise<void> {
  const results = await new AxeBuilder({ page }).disableRules(AXE_DISABLE).analyze()
  const serious = results.violations.filter(
    (v) => v.impact === 'serious' || v.impact === 'critical',
  )
  expect(serious, JSON.stringify(serious, null, 2)).toEqual([])
}

test.describe('axe a11y', () => {
  for (const route of ROUTES) {
    test(`axe ${route}`, async ({ page }) => {
      await preparePage(page)
      await page.goto(route)
      await settle(page)
      await assertAxe(page)
    })
  }

  test('axe onboarding', async ({ page }) => {
    await preparePage(page, { onboarded: false })
    await page.goto('/')
    await settle(page)
    await assertAxe(page)
  })
})
