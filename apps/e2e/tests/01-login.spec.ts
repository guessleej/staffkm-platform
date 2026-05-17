import { test, expect } from '@playwright/test'
import { loginAsAdmin } from '../fixtures/admin'

test.describe('P0: Login flow', () => {
  test('admin login redirects to dashboard', async ({ page }) => {
    await loginAsAdmin(page)
    // 任一受保護頁應載入完成
    await expect(page.locator('h1, [data-h1], [class*="text-2xl"]')).toBeVisible({ timeout: 5_000 })
    // localStorage 應有 token
    const hasToken = await page.evaluate(() => !!localStorage.getItem('access_token'))
    expect(hasToken).toBe(true)
  })

  test('wrong password shows error toast/inline', async ({ page }) => {
    await page.goto('/login')
    await page.evaluate(() => { localStorage.clear() })
    await page.goto('/login')
    await page.locator('input[autocomplete="username"]').fill('admin')
    await page.locator('input[type="password"]').fill('wrong_password_xxx')
    await page.locator('button[type="submit"]').click()
    // error message visible
    await expect(page.locator('text=/錯誤|invalid|fail/i')).toBeVisible({ timeout: 5_000 })
    // URL still /login
    await expect(page).toHaveURL(/\/login/)
  })
})
