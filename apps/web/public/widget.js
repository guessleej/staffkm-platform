/**
 * staffKM Embeddable Chat Widget
 *
 * Usage:
 *   <script src="https://staffkm.example.com/widget.js"
 *           data-app-id="YOUR_APP_UUID"
 *           data-host="https://staffkm.example.com"
 *           data-position="bottom-right"
 *           data-color="#4f46e5"
 *           data-label="有問題嗎？"
 *           defer></script>
 *
 * Requirements:
 *   - Target application must be `is_public = true`
 *   - data-host defaults to current script origin
 *   - data-position: bottom-right | bottom-left
 *
 * 沒任何外部依賴。打包後 ~3 KB gzipped。
 */
(function () {
  'use strict'

  // ── locate own script tag ──────────────────────
  var thisScript = document.currentScript
    || (function () {
         var s = document.getElementsByTagName('script')
         return s[s.length - 1]
       })()
  if (!thisScript) { console.warn('[staffKM] cannot locate script tag'); return }

  var appId    = thisScript.getAttribute('data-app-id')
  if (!appId) { console.warn('[staffKM] missing data-app-id'); return }

  var host     = thisScript.getAttribute('data-host')
                  || new URL(thisScript.src).origin
  var position = thisScript.getAttribute('data-position') || 'bottom-right'
  var color    = thisScript.getAttribute('data-color')    || '#4f46e5'
  var label    = thisScript.getAttribute('data-label')    || '有問題嗎？'

  // ── prevent double-mount ───────────────────────
  if (window.__staffkmWidgetMounted) return
  window.__staffkmWidgetMounted = true

  // ── style ──────────────────────────────────────
  var posCSS = position === 'bottom-left'
    ? 'left: 24px;'
    : 'right: 24px;'

  var css = (
    '#__staffkm-w-launcher{position:fixed;bottom:24px;' + posCSS +
      'z-index:2147483646;display:flex;align-items:center;gap:8px;' +
      'padding:12px 18px;border-radius:9999px;border:0;cursor:pointer;' +
      'color:#fff;background:' + color + ';' +
      'box-shadow:0 8px 24px rgba(0,0,0,0.18);' +
      'font:600 14px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;' +
      'transition:transform 150ms ease, box-shadow 150ms ease;}' +
    '#__staffkm-w-launcher:hover{transform:translateY(-2px);box-shadow:0 12px 28px rgba(0,0,0,0.22);}' +
    '#__staffkm-w-launcher svg{width:18px;height:18px;}' +
    '#__staffkm-w-frame{position:fixed;bottom:96px;' + posCSS +
      'z-index:2147483647;width:380px;height:600px;max-width:calc(100vw - 32px);max-height:calc(100vh - 120px);' +
      'border-radius:16px;overflow:hidden;border:1px solid rgba(0,0,0,0.08);' +
      'box-shadow:0 20px 50px rgba(0,0,0,0.25);' +
      'background:#fff;transform-origin:bottom right;' +
      'transform:scale(0.95) translateY(8px);opacity:0;' +
      'transition:transform 200ms ease, opacity 200ms ease;' +
      'pointer-events:none;}' +
    '#__staffkm-w-frame.__open{transform:scale(1) translateY(0);opacity:1;pointer-events:auto;}' +
    '#__staffkm-w-frame iframe{width:100%;height:100%;border:0;display:block;}' +
    '@media (max-width:480px){#__staffkm-w-frame{width:calc(100vw - 24px);height:75vh;bottom:88px;}}'
  )

  var styleEl = document.createElement('style')
  styleEl.id = '__staffkm-w-style'
  styleEl.appendChild(document.createTextNode(css))
  document.head.appendChild(styleEl)

  // ── launcher button ────────────────────────────
  var launcher = document.createElement('button')
  launcher.id = '__staffkm-w-launcher'
  launcher.type = 'button'
  launcher.setAttribute('aria-label', label)
  launcher.innerHTML =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">' +
    '<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>' +
    '</svg><span>' + escapeHtml(label) + '</span>'
  document.body.appendChild(launcher)

  // ── frame (lazy-create on first click) ─────────
  var frame = null
  function ensureFrame() {
    if (frame) return frame
    frame = document.createElement('div')
    frame.id = '__staffkm-w-frame'
    var iframe = document.createElement('iframe')
    iframe.src = host + '/share/' + encodeURIComponent(appId) + '?embed=1'
    iframe.allow = 'clipboard-write'
    iframe.setAttribute('title', 'staffKM Chat')
    frame.appendChild(iframe)
    document.body.appendChild(frame)
    return frame
  }

  var open = false
  function toggle() {
    var f = ensureFrame()
    open = !open
    if (open) {
      f.classList.add('__open')
      launcher.setAttribute('aria-expanded', 'true')
    } else {
      f.classList.remove('__open')
      launcher.setAttribute('aria-expanded', 'false')
    }
  }
  launcher.addEventListener('click', toggle)

  // ── ESC closes frame ───────────────────────────
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && open) toggle()
  })

  // ── close on click outside frame (option) ──────
  document.addEventListener('click', function (e) {
    if (!open || !frame) return
    if (frame.contains(e.target) || launcher.contains(e.target)) return
    // 只在使用者點空白處關（避免點下面內容打字）
    if (e.target === document.documentElement || e.target === document.body) toggle()
  })

  // ── public API ─────────────────────────────────
  window.staffKM = {
    open:   function () { if (!open) toggle() },
    close:  function () { if (open) toggle() },
    toggle: toggle,
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;')
  }
})();
