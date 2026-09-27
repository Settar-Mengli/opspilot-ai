import { defineConfig, devices } from '@playwright/test'

const PORT = 4173
const BASE_URL = `http://127.0.0.1:${PORT}`

/** Deterministic Chromium rasterization for E0 cross-run (amendment C). */
const DETERMINISTIC_CHROMIUM_ARGS = [
  '--disable-skia-runtime-opts',
  '--font-render-hinting=none',
  '--disable-font-subpixel-positioning',
  '--disable-lcd-text',
  '--force-color-profile=srgb',
  '--disable-gpu',
]

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  timeout: 60_000,
  expect: {
    toHaveScreenshot: {
      maxDiffPixels: 0,
      animations: 'disabled',
      caret: 'hide',
    },
  },
  use: {
    baseURL: BASE_URL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    locale: 'en-US',
    timezoneId: 'UTC',
    colorScheme: 'light',
  },
  projects: [
    {
      name: 'chromium-375',
      use: {
        // Avoid devices['iPhone 13'] + launchOptions clash; keep mobile viewport/touch.
        browserName: 'chromium',
        viewport: { width: 375, height: 812 },
        deviceScaleFactor: 1,
        isMobile: true,
        hasTouch: true,
        launchOptions: { args: DETERMINISTIC_CHROMIUM_ARGS },
      },
    },
    {
      name: 'chromium-768',
      use: {
        browserName: 'chromium',
        viewport: { width: 768, height: 1024 },
        deviceScaleFactor: 1,
        launchOptions: { args: DETERMINISTIC_CHROMIUM_ARGS },
      },
    },
    {
      name: 'chromium-1280',
      use: {
        browserName: 'chromium',
        viewport: { width: 1280, height: 800 },
        deviceScaleFactor: 1,
        launchOptions: { args: DETERMINISTIC_CHROMIUM_ARGS },
      },
    },
  ],
  webServer: {
    command: `npm run build && npm run preview -- --host 127.0.0.1 --port ${PORT}`,
    url: BASE_URL,
    reuseExistingServer: false,
    timeout: 180_000,
  },
  snapshotPathTemplate: '{testDir}/{testFileDir}/{testFileName}-snapshots/{arg}-{projectName}-linux{ext}',
})
