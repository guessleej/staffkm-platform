import { defineConfig, devices } from '@playwright/test'

/**
 * staffKM E2E tests — Playwright
 *
 * 5 個 P0 critical-path spec：
 *   1. login flow
 *   2. login + CAPTCHA after 3 failures
 *   3. create app + chat (with retry on stream)
 *   4. quota cap (admin set + 429)
 *   5. embed widget basic mount
 *
 * Run locally:    pnpm test
 * CI:             pnpm test --reporter=junit
 */
export default defineConfig({
  testDir: './tests',
  timeout: 30_000,
  expect: { timeout: 5_000 },
  fullyParallel: false,        // 共用 admin 帳號，避免 CAPTCHA 互打
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,                  // 同上
  reporter: [
    ['list'],
    ['html', { open: 'never' }],
  ],
  use: {
    baseURL: process.env.STAFFKM_BASE_URL || 'http://localhost',
    actionTimeout: 10_000,
    navigationTimeout: 15_000,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
})
