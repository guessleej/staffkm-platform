import { test, expect } from '@playwright/test'
import { loginAsAdmin } from '../fixtures/admin'

test.describe('P0: Knowledge Base flow', () => {
  test('KB list page + create button', async ({ page }) => {
    await loginAsAdmin(page)
    await page.goto('/knowledge')
    await expect(page.locator('h1')).toContainText(/知識庫|Knowledge/i)
    await expect(page.locator('text=/建立知識庫|Create KB|新增/').first()).toBeVisible()
  })

  test('create KB via API + verify list', async ({ page, request }) => {
    await loginAsAdmin(page)
    const token = await page.evaluate(() => localStorage.getItem('access_token'))
    expect(token).toBeTruthy()

    const name = `e2e-${Date.now()}`
    const r = await request.post('/api/v1/knowledge/bases', {
      headers: { Authorization: `Bearer ${token}` },
      data: { name, description: 'e2e test KB' },
    })
    expect(r.ok()).toBe(true)
    const body = await r.json()
    expect(body.data?.id).toBeTruthy()
    const kbId = body.data.id

    // 刷新 KB list 應看到
    await page.goto('/knowledge')
    await expect(page.locator(`text=${name}`)).toBeVisible({ timeout: 5_000 })

    // cleanup
    await request.delete(`/api/v1/knowledge/bases/${kbId}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
  })
})
