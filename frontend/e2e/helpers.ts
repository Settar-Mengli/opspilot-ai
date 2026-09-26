import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import type { Page, Route } from '@playwright/test'

const ROOT = path.dirname(fileURLToPath(import.meta.url))
const FIXTURES = path.join(ROOT, 'fixtures')
const FONTS = path.join(FIXTURES, 'fonts')

const FROZEN_ISO = '2026-09-26T15:00:00.000Z'

export type ApiMode =
  | 'ok'
  | 'down'
  | 'ask-error'
  | 'insights-error'
  | 'evening-error'
  | 'triage-error'

function readJson(name: string): unknown {
  return JSON.parse(fs.readFileSync(path.join(FIXTURES, name), 'utf-8'))
}

function readText(name: string): string {
  return fs.readFileSync(path.join(FIXTURES, name), 'utf-8')
}

async function fulfillJson(route: Route, body: unknown, status = 200): Promise<void> {
  await route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(body),
  })
}

async function fulfillText(route: Route, body: string, status = 200): Promise<void> {
  await route.fulfill({
    status,
    contentType: 'text/plain; charset=utf-8',
    body,
  })
}

export async function installFontFixtures(page: Page): Promise<void> {
  const cssPath = path.join(FONTS, 'google-fonts.css')
  let css = fs.readFileSync(cssPath, 'utf-8')
  const fontMap = JSON.parse(fs.readFileSync(path.join(FONTS, 'font-map.json'), 'utf-8')) as Array<{
    url: string
    file: string
  }>
  for (const entry of fontMap) {
    css = css.split(entry.url).join(`https://fonts.gstatic.com/e2e-fixtures/${entry.file}`)
  }

  await page.route(/fonts\.googleapis\.com\/css2/, async (route) => {
    await route.fulfill({ status: 200, contentType: 'text/css; charset=utf-8', body: css })
  })

  await page.route(/fonts\.gstatic\.com\/e2e-fixtures\/(.+)/, async (route, request) => {
    const match = request.url().match(/e2e-fixtures\/([^?/]+)/)
    const file = match?.[1]
    if (!file) {
      await route.abort()
      return
    }
    const filePath = path.join(FONTS, file)
    if (!fs.existsSync(filePath)) {
      await route.abort()
      return
    }
    await route.fulfill({
      status: 200,
      contentType: 'font/woff2',
      body: fs.readFileSync(filePath),
    })
  })
}

export async function mockApi(page: Page, mode: ApiMode = 'ok'): Promise<void> {
  const triage = readJson('triage.json')
  const settings = readJson('settings.json')
  const insights = readJson('insights.json')
  const capabilities = readJson('capabilities.json')
  const briefing = readText('briefing.txt')

  await page.route('**/api/v1/**', async (route) => {
    const url = new URL(route.request().url())
    const pathname = url.pathname
    const method = route.request().method()

    if (mode === 'down') {
      await route.abort('failed')
      return
    }

    if (pathname.endsWith('/health')) {
      await fulfillText(route, 'ok')
      return
    }
    if (pathname.endsWith('/triage') && method === 'GET') {
      if (mode === 'triage-error') {
        await fulfillJson(
          route,
          { error: { code: 'triage_failed', message: 'Triage fixture error', details: {} } },
          500,
        )
        return
      }
      await fulfillJson(route, triage)
      return
    }
    if (pathname.endsWith('/settings') && method === 'GET') {
      await fulfillJson(route, settings)
      return
    }
    if (pathname.endsWith('/briefing') && method === 'GET') {
      await fulfillText(route, briefing)
      return
    }
    if (pathname.endsWith('/ai-briefing') && method === 'GET') {
      await fulfillText(route, briefing)
      return
    }
    if (pathname.endsWith('/capabilities') && method === 'GET') {
      await fulfillJson(route, capabilities)
      return
    }
    if (pathname.endsWith('/runs') && method === 'GET') {
      await fulfillJson(route, [])
      return
    }
    if (pathname.endsWith('/inputs') && method === 'GET') {
      await fulfillJson(route, { files: ['sample_input.json'] })
      return
    }
    if (pathname.endsWith('/ask') && method === 'POST') {
      if (mode === 'ask-error') {
        await fulfillJson(
          route,
          { error: { code: 'ask_failed', message: 'Ask fixture error', details: {} } },
          500,
        )
        return
      }
      await fulfillJson(route, {
        answer: 'Checkout confirm is the priority. I can draft a status note when you want.',
      })
      return
    }
    if (pathname.endsWith('/evening-summary') && method === 'POST') {
      if (mode === 'evening-error') {
        await fulfillJson(
          route,
          { error: { code: 'evening_failed', message: 'Evening fixture error', details: {} } },
          500,
        )
        return
      }
      await fulfillJson(route, {
        summary: 'You cleared the urgent queue. Tomorrow starts with Q3 close prep.',
      })
      return
    }
    if (pathname.endsWith('/insights') && method === 'POST') {
      if (mode === 'insights-error') {
        await fulfillJson(
          route,
          { error: { code: 'insights_failed', message: 'Insights fixture error', details: {} } },
          500,
        )
        return
      }
      await fulfillJson(route, insights)
      return
    }

    await fulfillJson(route, { error: { code: 'unmocked', message: pathname, details: {} } }, 404)
  })
}

export async function seedOnboarded(page: Page): Promise<void> {
  await page.addInitScript(() => {
    window.localStorage.setItem('opspilot.userName', 'Alex')
    window.localStorage.setItem('opspilot.assistantName', 'Bulbul')
    const fixed = Date.parse('2026-09-26T15:00:00.000Z')
    Date.now = () => fixed
  })
}

export async function seedFresh(page: Page): Promise<void> {
  await page.addInitScript(() => {
    window.localStorage.removeItem('opspilot.userName')
    window.localStorage.removeItem('opspilot.assistantName')
    const fixed = Date.parse('2026-09-26T15:00:00.000Z')
    Date.now = () => fixed
  })
}

export async function preparePage(
  page: Page,
  opts: { mode?: ApiMode; onboarded?: boolean } = {},
): Promise<void> {
  const onboarded = opts.onboarded ?? true
  if (onboarded) {
    await seedOnboarded(page)
  } else {
    await seedFresh(page)
  }
  await page.clock.install({ time: new Date(FROZEN_ISO) })
  await installFontFixtures(page)
  await mockApi(page, opts.mode ?? 'ok')
}

export async function settle(page: Page): Promise<void> {
  await page.addStyleTag({
    content: `
      /* Monospace + geometric AA: Docker Desktop (Windows) vs GHA Linux share baselines. */
      html, body, body * {
        font-family: "Courier New", Courier, monospace !important;
        font-style: normal !important;
        letter-spacing: 0 !important;
        -webkit-font-smoothing: none !important;
        -moz-osx-font-smoothing: unset !important;
        text-rendering: geometricPrecision !important;
      }
      *, *::before, *::after {
        animation: none !important;
        transition: none !important;
        caret-color: transparent !important;
      }
      *:focus, *:focus-visible {
        outline: none !important;
        box-shadow: none !important;
      }
    `,
  })
  // Beat AskPanel's 200ms autofocus so focus rings don't flake screenshots.
  await page.waitForTimeout(250)
  await page.evaluate(() => {
    const active = document.activeElement
    if (active && active instanceof HTMLElement) {
      active.blur()
    }
  })
  await page.waitForLoadState('networkidle')
  await page.waitForTimeout(150)
}
