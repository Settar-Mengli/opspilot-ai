import { test, expect } from '@playwright/test'
import { preparePage, settle } from './helpers'

test.describe('overlay stack behaviors', () => {
  test('Escape closes topmost overlay only', async ({ page }) => {
    test.skip(
      test.info().project.name === 'chromium-1280',
      'Ask is docked at ≥1280; modal Escape stack covered in desktop-layout.spec',
    )
    await preparePage(page)
    await page.goto('/dashboard')
    await settle(page)

    await page.locator('.dash-hero').click()
    await expect(page.locator('.slide-panel').first()).toBeVisible()

    const modifier = process.platform === 'darwin' ? 'Meta' : 'Control'
    await page.keyboard.press(`${modifier}+KeyK`)
    await expect(page.locator('.ask-panel')).toBeVisible()

    await page.keyboard.press('Escape')
    await expect(page.locator('.ask-panel')).toHaveCount(0)
    await expect(page.locator('.slide-panel').first()).toBeVisible()

    await page.keyboard.press('Escape')
    await expect(page.locator('.slide-panel')).toHaveCount(0)
  })

  test('scroll lock refcount unlocks only after last overlay closes', async ({ page }) => {
    test.skip(
      test.info().project.name === 'chromium-1280',
      'Ask is docked at ≥1280; modal scroll lock covered below 1280',
    )
    await preparePage(page)
    await page.goto('/dashboard')
    await settle(page)

    await page.locator('.dash-hero').click()
    await expect(page.locator('.slide-panel').first()).toBeVisible()
    await expect.poll(async () => page.evaluate(() => document.body.style.overflow)).toBe('hidden')

    const modifier = process.platform === 'darwin' ? 'Meta' : 'Control'
    await page.keyboard.press(`${modifier}+KeyK`)
    await expect(page.locator('.ask-panel')).toBeVisible()
    await expect.poll(async () => page.evaluate(() => document.body.style.overflow)).toBe('hidden')

    await page.keyboard.press('Escape')
    await expect(page.locator('.ask-panel')).toHaveCount(0)
    await expect.poll(async () => page.evaluate(() => document.body.style.overflow)).toBe('hidden')

    await page.keyboard.press('Escape')
    await expect(page.locator('.slide-panel')).toHaveCount(0)
    await expect.poll(async () => page.evaluate(() => document.body.style.overflow)).not.toBe('hidden')
  })

  test('focus trap keeps Tab inside the dialog', async ({ page }) => {
    test.skip(
      test.info().project.name === 'chromium-1280',
      'Ask modal focus trap applies below 1280 only',
    )
    await preparePage(page)
    await page.goto('/dashboard')
    await settle(page)

    await page.getByRole('button', { name: /just ask me/i }).click()
    const dialog = page.getByRole('dialog', { name: /Ask /i })
    await expect(dialog).toBeVisible()

    for (let i = 0; i < 8; i++) {
      await page.keyboard.press('Tab')
      const inside = await page.evaluate(() => {
        const el = document.activeElement
        const dlg = document.querySelector('.ask-panel')
        return !!(el && dlg && dlg.contains(el))
      })
      expect(inside).toBe(true)
    }
  })

  test('focus trap Shift+Tab stays inside the dialog', async ({ page }) => {
    test.skip(
      test.info().project.name === 'chromium-1280',
      'Ask modal focus trap applies below 1280 only',
    )
    await preparePage(page)
    await page.goto('/dashboard')
    await settle(page)

    await page.getByRole('button', { name: /just ask me/i }).click()
    const dialog = page.getByRole('dialog', { name: /Ask /i })
    await expect(dialog).toBeVisible()

    for (let i = 0; i < 8; i++) {
      await page.keyboard.press('Shift+Tab')
      const inside = await page.evaluate(() => {
        const el = document.activeElement
        const dlg = document.querySelector('.ask-panel')
        return !!(el && dlg && dlg.contains(el))
      })
      expect(inside).toBe(true)
    }
  })

  test('return-focus restores the opener after close', async ({ page }) => {
    await preparePage(page)
    await page.goto('/dashboard')
    await settle(page)

    const opener = page.getByRole('button', { name: /whole week/i })
    await opener.focus()
    await expect(opener).toBeFocused()
    await opener.click()

    const dialog = page.getByRole('dialog', { name: /whole week/i })
    await expect(dialog).toBeVisible()

    await page.keyboard.press('Escape')
    await expect(dialog).toHaveCount(0)
    await expect(opener).toBeFocused()
  })

  test('panels expose dialog ARIA', async ({ page }) => {
    await preparePage(page)
    await page.goto('/dashboard')
    await settle(page)

    await page.locator('.dash-hero').click()
    const priorities = page.getByRole('dialog').first()
    await expect(priorities).toHaveAttribute('aria-modal', 'true')
    await expect(priorities).toHaveAttribute('aria-labelledby', /.+/)
    await page.keyboard.press('Escape')

    await page.getByRole('button', { name: /wrap up the day/i }).click()
    const evening = page.getByRole('dialog', { name: /wrap up the day/i })
    await expect(evening).toHaveAttribute('aria-modal', 'true')

    await page.keyboard.press('Escape')
    await page.getByRole('button', { name: /whole week/i }).click()
    await expect(page.getByRole('dialog', { name: /whole week/i })).toHaveAttribute(
      'aria-modal',
      'true',
    )
    await page.keyboard.press('Escape')

    if (test.info().project.name !== 'chromium-1280') {
      await page.getByRole('button', { name: /just ask me/i }).click()
      await expect(page.getByRole('dialog', { name: /Ask /i })).toHaveAttribute('aria-modal', 'true')
      await page.keyboard.press('Escape')
    }

    await page.locator('.bell-btn').first().click()
    await expect(page.getByRole('dialog').first()).toHaveAttribute('aria-modal', 'true')
  })
})
