/**
 * Admin login helpers — 共用 fixture
 */
import { test as base, expect, type Page } from '@playwright/test'

const ADMIN_USERNAME = process.env.STAFFKM_ADMIN_USERNAME || 'admin'
const ADMIN_PASSWORD = process.env.STAFFKM_ADMIN_PASSWORD || 'Admin@2026'

export async function loginAsAdmin(page: Page) {
  await page.goto('/login')
  // 先清 storage（避免 stale token）
  await page.evaluate(() => { localStorage.clear(); sessionStorage.clear() })
  await page.goto('/login')
  await page.locator('input[autocomplete="username"]').fill(ADMIN_USERNAME)
  await page.locator('input[type="password"]').fill(ADMIN_PASSWORD)
  await page.locator('button[type="submit"]').click()
  // 等 redirect 完成
  await expect(page).toHaveURL(/\/(chat|applications|admin\/.*)/, { timeout: 15_000 })
}

/** 透過 API 清 CAPTCHA 計數 — 給 negative test 後清場 */
export async function clearCaptchaState(page: Page) {
  await page.request.post('/api/v1/admin/_test/reset-captcha').catch(() => { /* endpoint 不存在沒關係 */ })
}

export { base as test, expect }
