import { test, expect } from '@playwright/test'
import { loginAsAdmin } from '../fixtures/admin'

/**
 * P0：對話渲染 last-mile（SSE 換行 → marked → DOM 分明）。
 *
 * 補唯一未被守住的一哩：unit(test_sse_guard) + live E2E(e2e_smoke) 已守 SSE 鏈本身，
 * 但「marked → 真實 DOM」這段只有瀏覽器跑得到。本 spec 攔截串流、餵 gemma4 風格
 * 「換行單獨成 token」(純 \n\n / \n) 的條列答案，斷言渲染成**結構化 DOM**（<ol>/<li>/
 * <br>/多個 <p>），而非擠成一坨的單一純文字 —— 直接守 v5.9.32/v5.10.13/v5.11.6/v5.11.8
 * 整條換行回歸史的「使用者眼睛看到的結果」。
 *
 * 確定性：用 page.route 餵罐裝 SSE（不依賴 LLM）→ 不 flaky。
 */

const EOL = '\r\n'

/** 模擬 chat-service 中繼送給前端的 SSE（每個 token 一個 event；換行單獨成 token）。 */
function sseBody(tokens: string[]): string {
  let out = ''
  for (const t of tokens) {
    out += `event: token${EOL}`
    for (const line of t.split('\n')) out += `data: ${line}${EOL}` // 多行 data（sse-starlette 風格）
    out += EOL
  }
  out += `event: citations${EOL}data: []${EOL}${EOL}`
  out += `event: done${EOL}data: [DONE]${EOL}${EOL}`
  return out
}

test.describe('P0: 對話渲染（SSE 換行 → marked → DOM 分明）', () => {
  test('條列答案渲染成結構化 DOM，不擠成一坨', async ({ page }) => {
    test.setTimeout(60_000)
    await loginAsAdmin(page)

    // gemma4 風格：換行單獨成 token（純 "\n\n" / "\n"）— 正是 v5.11.6 的回歸來源
    const tokens = [
      '請假步驟：', '\n\n',
      '1. 查規定', '\n',
      '2. 填單', '\n',
      '3. 送主管核准',
    ]
    await page.route('**/messages/stream', async (route) => {
      await route.fulfill({
        status: 200,
        headers: {
          'content-type': 'text/event-stream; charset=utf-8',
          'cache-control': 'no-cache',
        },
        body: sseBody(tokens),
      })
    })

    await page.goto('/chat')
    const input = page.locator('textarea').first()
    await expect(input).toBeVisible({ timeout: 15_000 })
    await input.fill('我要如何請假？')
    await input.press('Enter')

    // 等 assistant 訊息渲染
    const md = page.locator('.md-body').last()
    await expect(md).toBeVisible({ timeout: 30_000 })
    await expect(md).toContainText('查規定', { timeout: 30_000 })

    // ── 核心斷言：分明結構，而非單一純文字（擠成一坨）──
    const html = await md.innerHTML()
    const blockStructure =
      /<li[\s>]/.test(html) ||
      /<ol[\s>]|<ul[\s>]/.test(html) ||
      /<br\s*\/?>/.test(html) ||
      (html.match(/<p[\s>]/g)?.length ?? 0) >= 2
    expect(blockStructure, `渲染擠成一坨（無區塊結構）：${html.slice(0, 240)}`).toBeTruthy()

    // 三個項目都看得到（換行沒被吃掉 → 條列完整）
    for (const item of ['查規定', '填單', '送主管核准']) {
      await expect(md).toContainText(item)
    }
  })
})
