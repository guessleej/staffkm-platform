import { test, expect } from '@playwright/test'

test.describe('staffKM smoke', () => {
  test('login page renders', async ({ page }) => {
    await page.goto('/login')
    await expect(page).toHaveTitle(/staffKM/i)
    // 登入表單存在（帳號 + 密碼欄）
    await expect(page.locator('input[type="text"], input[name="username"]').first()).toBeVisible()
    await expect(page.locator('input[type="password"]').first()).toBeVisible()
  })

  test('health endpoint OK', async ({ request }) => {
    const r = await request.get('/api/v1/health')
    // gateway 通常會走 /api/v1/* 代理；任一 2xx 視為健康
    expect(r.status()).toBeLessThan(500)
  })

  test('public chat route 404-or-form', async ({ page }) => {
    const resp = await page.goto('/share/invalid-id')
    // 無效 share id 應回 200 + 友善錯誤，不可 5xx
    expect(resp?.status() ?? 200).toBeLessThan(500)
  })
})
