/**
 * 對話渲染 last-mile 守衛（輕量、每 PR 跑、無瀏覽器/無 stack/無新依賴）。
 *
 * 用 app 同款 marked 設定（MarkdownMessage.vue：breaks:true, gfm:true）渲染「gemma4 風格
 * 換行單獨成 token」經前端 SSE parse 後的內容，斷言渲染成結構化 HTML（<ol>/<li>/<br>/多 <p>），
 * 而非擠成一坨的單一純文字。對照組（換行被吃）必須判為「擠成一坨」→ 證明斷言有鑑別力。
 *
 * 真實瀏覽器 Playwright（apps/e2e/06-chat-render）仍在 playwright-e2e.yml（需 served app）；
 * 本檔補「每個 PR 都跑」的那一層。run: cd apps/web && node test/render-guard.mjs
 */
import { marked } from 'marked'

marked.setOptions({ breaks: true, gfm: true })

const EOL = '\r\n'
// gemma4 風格：換行單獨成 token（純 \n\n / \n）— v5.9.32/v5.10.13/v5.11.6/v5.11.8 回歸來源
const tokens = ['請假步驟：', '\n\n', '1. 查規定', '\n', '2. 填單', '\n', '3. 送主管核准']

function sseBody(ts) {
  let o = ''
  for (const t of ts) { o += `event: token${EOL}`; for (const l of t.split('\n')) o += `data: ${l}${EOL}`; o += EOL }
  o += `event: done${EOL}data: [DONE]${EOL}${EOL}`
  return o
}

// 複製前端 streamChat flush（事件感知、多行 data 用 \n 重組、v5.11.8 保留純換行）
function parse(raw) {
  let out = '', data = [], ev = ''
  const flush = () => {
    if (!ev && !data.length) return
    const d = data.join('\n'); const trimmed = d.trim(); ev = ''; data = []
    if (trimmed === '[DONE]') return
    if (d === '') return
    out += d
  }
  for (const rl of raw.split('\n')) {
    const line = rl.replace(/\r$/, '')
    if (line === '') { flush(); continue }
    if (line.startsWith('event:')) { ev = line.slice(6).trim(); continue }
    if (line.startsWith('data:')) { const s = line.slice(5); data.push(s.startsWith(' ') ? s.slice(1) : s) }
  }
  flush(); return out
}

function isStructured(html) {
  return /<li[\s>]/.test(html) || /<ol[\s>]|<ul[\s>]/.test(html) ||
    /<br\s*\/?>/.test(html) || (html.match(/<p[\s>]/g)?.length ?? 0) >= 2
}

const content = parse(sseBody(tokens))
const fixedHtml = marked.parse(content, { async: false })
const wallHtml = marked.parse(content.replace(/\n/g, ''), { async: false })  // 對照：換行被吃

const fails = []
if (content !== '請假步驟：\n\n1. 查規定\n2. 填單\n3. 送主管核准')
  fails.push(`SSE parse 內容不符: ${JSON.stringify(content)}`)
if (!isStructured(fixedHtml)) fails.push(`fixed 未渲染成結構化 DOM: ${fixedHtml.slice(0, 160)}`)
if (isStructured(wallHtml)) fails.push(`對照組(換行被吃)竟也判為結構化 → 斷言無鑑別力`)
for (const item of ['查規定', '填單', '送主管核准'])
  if (!fixedHtml.includes(item)) fails.push(`渲染缺項目: ${item}`)

if (fails.length) {
  console.error('❌ 對話渲染守衛失敗:\n  - ' + fails.join('\n  - '))
  process.exit(1)
}
console.log('✅ 對話渲染守衛通過：SSE 換行→marked→結構化 DOM（<ol><li>），對照組正確判為擠成一坨。')
