// 安全的 UUID v4 產生器。
//
// 雷：`crypto.randomUUID()` 只在「安全環境」（HTTPS 或 localhost）可用；
// 純 HTTP 部署（如地端 http://192.168.11.50）下 `crypto.randomUUID` 是 undefined，
// 呼叫即丟 `TypeError: crypto.randomUUID is not a function`，會炸掉整個送出流程。
// `crypto.getRandomValues` 則**不限**安全環境，HTTP 也能用 → 用它組 v4。
// 三層退路：randomUUID（安全環境）→ getRandomValues（HTTP）→ Math.random（極端後備）。
export function uuid(): string {
  const c = globalThis.crypto as Crypto | undefined
  if (c && typeof c.randomUUID === 'function') {
    return c.randomUUID()
  }
  if (c && typeof c.getRandomValues === 'function') {
    const b = c.getRandomValues(new Uint8Array(16))
    b[6] = (b[6] & 0x0f) | 0x40 // version 4
    b[8] = (b[8] & 0x3f) | 0x80 // variant 10
    const h = Array.from(b, (x) => x.toString(16).padStart(2, '0'))
    return `${h[0]}${h[1]}${h[2]}${h[3]}-${h[4]}${h[5]}-${h[6]}${h[7]}-${h[8]}${h[9]}-${h[10]}${h[11]}${h[12]}${h[13]}${h[14]}${h[15]}`
  }
  // 極端後備（無 crypto）：非密碼學強度，僅供前端臨時 message id 用
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (ch) => {
    const r = (Math.random() * 16) | 0
    const v = ch === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}
