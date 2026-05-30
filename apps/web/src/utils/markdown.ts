import { marked } from 'marked'
import DOMPurify from 'dompurify'

marked.setOptions({ breaks: true, gfm: true })

/**
 * v5.12 安全渲染：把 markdown 轉成「已消毒」HTML 字串供 v-html 使用。
 *
 * ⚠ LLM 回覆 / RAG 命中內容 / 使用者輸入皆視為不可信來源。marked 預設**會輸出 raw HTML**
 *   （`<img src=x onerror=...>` / `<script>`），未消毒直接 v-html = XSS。一律先 DOMPurify.sanitize。
 *   任何要 v-html 渲染 markdown 的地方都應走這支 util，不要自己 marked.parse。
 */
export function renderMarkdown(src: string): string {
  const text = src || ''
  try {
    const raw = marked.parse(text, { async: false }) as string
    return DOMPurify.sanitize(raw)
  } catch {
    // 解析失敗 → 退回純文字（仍消毒，保留換行）
    const escaped = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/\n/g, '<br>')
    return DOMPurify.sanitize(escaped)
  }
}

/**
 * 純文字 HTML 轉義（給「把使用者字串拼進 HTML」的場景，如 highlight 標記）。
 */
export function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}
