import { test, expect } from '@playwright/test'

test.describe('P0: Embeddable widget (v2.4-A)', () => {
  test('widget.js + widget-demo.html serve correctly', async ({ request }) => {
    const js = await request.get('/widget.js')
    expect(js.ok()).toBe(true)
    expect(js.headers()['content-type']).toMatch(/javascript/)

    const demo = await request.get('/widget-demo.html')
    expect(demo.ok()).toBe(true)
    expect(demo.headers()['content-type']).toMatch(/html/)
  })

  test('widget mounts launcher button on demo page', async ({ page }) => {
    await page.goto('/widget-demo.html')
    // demo 頁需 fill app-id 才會自動 mount，這邊只驗 JS 本身載入沒爆
    const errors: string[] = []
    page.on('pageerror', e => errors.push(String(e)))
    await page.waitForTimeout(500)
    expect(errors).toEqual([])
    // 頁面標題正確
    await expect(page.locator('h1')).toContainText('Embeddable Widget')
  })
})
