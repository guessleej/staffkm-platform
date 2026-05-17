import { test, expect } from '@playwright/test'

test.describe('P0: CAPTCHA after 3 failed login attempts', () => {
  test('4th wrong attempt requires CAPTCHA', async ({ page, request }) => {
    // 用獨立 username 不影響其他 test 對 admin 的 CAPTCHA counter
    const u = `e2e_${Date.now()}`
    for (let i = 0; i < 3; i++) {
      const r = await request.post('/api/v1/auth/login', {
        data: { username: u, password: 'definitely-wrong' },
        failOnStatusCode: false,
      })
      expect(r.status()).toBe(401)
    }
    // 4th: 應拿到 captcha_required
    const r4 = await request.post('/api/v1/auth/login', {
      data: { username: u, password: 'definitely-wrong' },
      failOnStatusCode: false,
    })
    expect([401, 403]).toContain(r4.status())  // 401 detail captcha_required 或 403 captcha_required
    const body = await r4.json()
    expect(body.detail).toMatch(/captcha/)
  })

  test('GET /auth/captcha returns token + question', async ({ request }) => {
    const r = await request.get('/api/v1/auth/captcha')
    expect(r.ok()).toBe(true)
    const body = await r.json()
    expect(body.data.token).toBeTruthy()
    expect(body.data.question).toMatch(/[\d+\-*]/)
  })
})
