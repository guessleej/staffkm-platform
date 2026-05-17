import { test, expect } from '@playwright/test'
import { loginAsAdmin } from '../fixtures/admin'

test.describe('P0: Application CRUD', () => {
  test('list applications page renders', async ({ page }) => {
    await loginAsAdmin(page)
    await page.goto('/applications')
    await expect(page.locator('h1')).toContainText(/應用|Application/i)
    // 預設應有「新增」按鈕 (admin role)
    await expect(page.locator('text=/新增|Create/i')).toBeVisible()
  })

  test('template gallery opens via ?tour=templates', async ({ page }) => {
    await loginAsAdmin(page)
    await page.goto('/applications?tour=templates')
    // 模板 gallery modal 應自動開
    await expect(page.locator('text=/挑一個模板|template/i')).toBeVisible({ timeout: 5_000 })
    // 至少 1 個 built-in 模板卡片
    await expect(page.locator('text=/內部知識問答|客服 FAQ|合約審閱/').first()).toBeVisible()
  })
})
