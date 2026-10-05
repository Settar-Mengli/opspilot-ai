import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import type { Page, Route } from '@playwright/test'

const ROOT = path.dirname(fileURLToPath(import.meta.url))
const FIXTURES = path.join(ROOT, 'fixtures')
const FONTS = path.join(FIXTURES, 'fonts')

/** Night hour (02:00 UTC) → "Working late" (matches C-BASE -linux baselines). */
const FROZEN_ISO = '2026-09-26T02:00:00.000Z'

export async function seedOnboarded(page: Page): Promise<void> {
  await page.addInitScript(() => {
    window.localStorage.setItem('opspilot.userName', 'Alex')
    window.localStorage.setItem('opspilot.assistantName', 'Bulbul')
  })
}

export async function seedFresh(page: Page): Promise<void> {
  await page.addInitScript(() => {
    window.localStorage.removeItem('opspilot.userName')
    window.localStorage.removeItem('opspilot.assistantName')
  })
}

export type ApiMode =
  | 'ok'
  | 'down'
  | 'ask-error'
  | 'insights-error'
  | 'evening-error'
  | 'triage-error'
  | 'connected'
  | 'sync-progress'
  | 'sync-triaging'
  | 'sync-done'
  | 'sync-busy'
  | 'job-status'
  | 'correction'
  | 'draft-failed'

/** Credentialed FE calls (credentials:'include') reject ACAO:* — mirror preview origin. */
const CORS_HEADERS: Record<string, string> = {
  'Access-Control-Allow-Origin': 'http://127.0.0.1:4173',
  'Access-Control-Allow-Credentials': 'true',
  'Access-Control-Allow-Methods': 'GET,POST,DELETE,OPTIONS',
  'Access-Control-Allow-Headers': 'content-type,x-requested-with',
}

function isConnectedMode(mode: ApiMode): boolean {
  return (
    mode === 'connected' ||
    mode === 'correction' ||
    mode === 'sync-progress' ||
    mode === 'sync-triaging' ||
    mode === 'sync-done' ||
    mode === 'sync-busy' ||
    mode === 'job-status'
  )
}

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
    headers: CORS_HEADERS,
    body: JSON.stringify(body),
  })
}

async function fulfillText(route: Route, body: string, status = 200): Promise<void> {
  await route.fulfill({
    status,
    contentType: 'text/plain; charset=utf-8',
    headers: CORS_HEADERS,
    body,
  })
}

async function fulfillSse(route: Route, body: string): Promise<void> {
  await route.fulfill({
    status: 200,
    contentType: 'text/event-stream',
    headers: {
      ...CORS_HEADERS,
      // Force the fetch reader to complete so later mail/draft calls are not starved.
      'Content-Length': String(Buffer.byteLength(body, 'utf8')),
      Connection: 'close',
    },
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
  type TriageRow = {
    id: string
    subject_or_title: string
    urgency: string
    urgency_reason: string
    category: string
    category_reason: string
    sentiment: string
    sentiment_reason: string
    corrected?: boolean
  }
  let triageRecords = readJson('triage.json') as TriageRow[]
  const settingsConnected = readJson('settings-connected.json')
  const settingsJobStatus = readJson('settings-job-status.json')
  const settingsBase = readJson('settings.json')
  const settings =
    mode === 'job-status'
      ? settingsJobStatus
      : isConnectedMode(mode) && mode !== 'job-status'
        ? settingsConnected
        : settingsBase
  const insights = readJson('insights.json')
  const capabilitiesConnected = readJson('capabilities-connected.json')
  const capabilitiesBase = readJson('capabilities.json')
  const capabilities = isConnectedMode(mode) ? capabilitiesConnected : capabilitiesBase
  const calendarWeek = readJson('calendar-week.json')
  const briefing = readText('briefing.txt')

  const syncCountsBase = {
    account_email: 'ops@example.com',
    gmail_upserted: 2,
    gmail_removed: 0,
    calendar_upserted: 1,
    gmail_total: 10,
    meetings_total: 4,
    calendar_truncated: false,
    gmail_truncated: false,
  }

  await page.route('**/api/v1/**', async (route) => {
    const url = new URL(route.request().url())
    const pathname = url.pathname
    const method = route.request().method()

    // Mail drafts handled by a later route (Playwright: last match wins).
    if (pathname.includes('/mail/drafts/')) {
      await route.fallback()
      return
    }

    if (method === 'OPTIONS') {
      await route.fulfill({
        status: 204,
        headers: CORS_HEADERS,
      })
      return
    }

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
      await fulfillJson(route, triageRecords)
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
    if (pathname.endsWith('/calendar/week') && method === 'GET') {
      await fulfillJson(route, calendarWeek)
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
    if (pathname.endsWith('/ask/stream') && method === 'POST') {
      if (mode === 'ask-error') {
        await fulfillSse(
          route,
          'data: {"type":"error","request_id":"e2e","code":"ask_failed","message":"Ask fixture error"}\n\n',
        )
        return
      }
      if (mode === 'draft-failed') {
        const answer = 'I drafted a reply for you.'
        // No SSE reopenable seed — gallery must click Approve → fail → Reopen (O1).
        await fulfillSse(
          route,
          `data: {"type":"token","request_id":"e2e","text":${JSON.stringify(answer)}}\n\n` +
            `data: {"type":"draft","request_id":"e2e","draft_id":"draft-fail-1","subject":"Re: Checkout errors","body":"Hi, we are investigating the checkout issue.","to_addrs":"customer@example.com"}\n\n` +
            `data: {"type":"final","request_id":"e2e","answer":${JSON.stringify(answer)}}\n\n`,
        )
        return
      }
      const answer = 'Checkout confirm is the priority. I can draft a status note when you want.'
      await fulfillSse(
        route,
        `data: {"type":"token","request_id":"e2e","text":${JSON.stringify(answer)}}\n\n` +
          `data: {"type":"final","request_id":"e2e","answer":${JSON.stringify(answer)}}\n\n`,
      )
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

    if (pathname.match(/\/corrections\//) && method === 'POST') {
      const workItemId = pathname.split('/').pop() || ''
      let urgency = 'medium'
      let category: string | undefined
      let sentiment: string | undefined
      try {
        const posted = route.request().postDataJSON() as {
          urgency?: string
          category?: string
          sentiment?: string
        }
        if (posted.urgency) urgency = posted.urgency
        category = posted.category
        sentiment = posted.sentiment
      } catch {
        // keep defaults
      }
      triageRecords = triageRecords.map((row) =>
        row.id === workItemId
          ? {
              ...row,
              urgency,
              category: category ?? row.category,
              sentiment: sentiment ?? row.sentiment,
              corrected: true,
            }
          : row,
      )
      await fulfillJson(route, { status: 'saved' })
      return
    }
    if (pathname.match(/\/corrections\//) && method === 'DELETE') {
      await fulfillJson(route, { status: 'deleted' })
      return
    }
    if (pathname.match(/\/jobs\//) && method === 'GET') {
      if (mode === 'sync-triaging') {
        await fulfillJson(route, {
          id: 'job-sync-1',
          job_kind: 'sync_drain',
          status: 'running',
          triaged: 0,
          pending: 5,
          error_code: null,
          run_id: null,
          created_at: '2026-09-26T02:00:00.000Z',
          started_at: '2026-09-26T02:00:00.000Z',
          finished_at: null,
        })
        return
      }
      if (mode === 'sync-done') {
        await fulfillJson(route, {
          id: 'job-sync-1',
          job_kind: 'sync_drain',
          status: 'succeeded',
          triaged: 4,
          pending: 1,
          error_code: null,
          run_id: null,
          created_at: '2026-09-26T02:00:00.000Z',
          started_at: '2026-09-26T02:00:00.000Z',
          finished_at: '2026-09-26T02:01:00.000Z',
        })
        return
      }
    }
    if (pathname.endsWith('/sync') && method === 'POST') {
      if (mode === 'sync-progress') {
        // Hold forever so the UI stays on Syncing… (no status line yet).
        await new Promise(() => {})
        return
      }
      if (mode === 'sync-busy') {
        await fulfillJson(route, {
          ...syncCountsBase,
          drain: 'busy',
          job_id: null,
          triaged: 0,
          pending: 5,
        })
        return
      }
      if (mode === 'sync-triaging' || mode === 'sync-done') {
        await fulfillJson(route, {
          ...syncCountsBase,
          drain: 'started',
          job_id: 'job-sync-1',
          triaged: 0,
          pending: 5,
        })
        return
      }
      await fulfillJson(route, {
        ...syncCountsBase,
        drain: 'not_needed',
        job_id: null,
        triaged: 0,
        pending: 0,
      })
      return
    }

    await fulfillJson(route, { error: { code: 'unmocked', message: pathname, details: {} } }, 404)
  })

  // Registered last → takes precedence for mail HITL (edit/approve/reopen).
  await page.route('**/api/v1/mail/drafts/**', async (route) => {
    const method = route.request().method()
    const pathname = new URL(route.request().url()).pathname
    if (method === 'OPTIONS') {
      await route.fulfill({ status: 204, headers: CORS_HEADERS })
      return
    }
    if (pathname.includes('/reopen') && method === 'POST') {
      await fulfillJson(route, {
        id: 'draft-reopened-1',
        status: 'pending_review',
        payload_sha256: 'abc123',
        error_code: null,
      })
      return
    }
    if (pathname.includes('/edit') && method === 'POST') {
      await fulfillJson(route, {
        id: mode === 'draft-failed' ? 'draft-fail-1' : 'draft-1',
        subject: 'Re: Checkout errors',
        body: 'Hi, we are investigating the checkout issue.',
        to_addrs: 'customer@example.com',
        payload_sha256: 'sha256-e2e-edit',
      })
      return
    }
    if (pathname.includes('/approve') && method === 'POST') {
      if (mode === 'draft-failed') {
        await fulfillJson(route, {
          status: 'failed',
          send_failed: false,
          error_code: 'google_reauth_required',
        })
        return
      }
      await fulfillJson(route, { status: 'sent' })
      return
    }
    await fulfillJson(route, { error: { code: 'unmocked_mail', message: pathname, details: {} } }, 404)
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
  await page.clock.setFixedTime(new Date(FROZEN_ISO))
  await installFontFixtures(page)
  await mockApi(page, opts.mode ?? 'ok')
}

/** Faces used by tokens.css — assert loaded before each screenshot (E0). */
const REQUIRED_FONT_CHECKS = [
  '400 16px Poppins',
  '500 16px Poppins',
  '600 16px Poppins',
  '700 16px Poppins',
  '400 16px Lora',
  '500 16px Lora',
  '600 16px Lora',
  'italic 400 16px Lora',
] as const

export async function settle(page: Page): Promise<void> {
  // Harness-only settle: kill motion, blur (Skia nondeterminism), scrollbars, caret.
  // Does not change app design tokens or substitute fonts.
  await page.addStyleTag({
    content: `
      *, *::before, *::after {
        animation: none !important;
        transition: none !important;
        caret-color: transparent !important;
        backdrop-filter: none !important;
        -webkit-backdrop-filter: none !important;
        /* Soft shadows/filters rasterize nondeterministically under Skia. */
        box-shadow: none !important;
        filter: none !important;
        text-shadow: none !important;
      }
      /* Deterministic SVG stroke rasterization (not a design-font override). */
      svg, svg * {
        shape-rendering: crispEdges !important;
      }
      html, body {
        overflow: hidden !important;
        scrollbar-width: none !important;
      }
      *::-webkit-scrollbar {
        width: 0 !important;
        height: 0 !important;
        display: none !important;
      }
    `,
  })
  // Beat AskPanel's 200ms autofocus; longer waits for GHA AA determinism (E0).
  await page.waitForTimeout(800)
  // Guard: C-BASE -linux greetings are night ("Working late"). Fail loud if clock drift.
  const hour = await page.evaluate(() => new Date().getHours())
  if (hour >= 5 && hour < 22) {
    throw new Error(
      `visual harness: expected night hour (Working late), got ${hour}. Check clock.setFixedTime + timezoneId UTC.`,
    )
  }
  await page.evaluate(async (requiredFonts: readonly string[]) => {
    if (document.fonts?.ready) {
      await document.fonts.ready
    }
    for (const spec of requiredFonts) {
      await document.fonts.load(spec)
    }
    await document.fonts.ready
    const missing = requiredFonts.filter((spec) => !document.fonts.check(spec))
    if (missing.length > 0) {
      throw new Error(`E0 font faces not loaded: ${missing.join(', ')}`)
    }
    // Decode any in-DOM images (icons served as <img> if present).
    const images = Array.from(document.images)
    await Promise.all(
      images.map(async (img) => {
        if (img.complete) return
        await img.decode().catch(() => undefined)
      }),
    )
    const blurActive = () => {
      const active = document.activeElement
      if (active && active instanceof HTMLElement) {
        active.blur()
      }
    }
    blurActive()
    await new Promise((r) => setTimeout(r, 50))
    blurActive()
    // Two animation frames so layout/paint settle after font swap.
    await new Promise<void>((resolve) => {
      requestAnimationFrame(() => requestAnimationFrame(() => resolve()))
    })
  }, REQUIRED_FONT_CHECKS)
  await page.waitForLoadState('networkidle')
  await page.waitForTimeout(500)
}
