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

test.describe('axe a11y', () => {
  for (const route of ROUTES) {
    test(`axe ${route}`, async ({ page }) => {
      await preparePage(page)
      await page.goto(route)
      await settle(page)
      const results = await new AxeBuilder({ page }).analyze()
      const serious = results.violations.filter(
        (v) => v.impact === 'serious' || v.impact === 'critical',
      )
      expect(serious, JSON.stringify(serious, null, 2)).toEqual([])
    })
  }

  test('axe onboarding', async ({ page }) => {
    await preparePage(page, { onboarded: false })
    await page.goto('/')
    await settle(page)
    const results = await new AxeBuilder({ page }).analyze()
    const serious = results.violations.filter(
      (v) => v.impact === 'serious' || v.impact === 'critical',
    )
    expect(serious, JSON.stringify(serious, null, 2)).toEqual([])
  })
})
