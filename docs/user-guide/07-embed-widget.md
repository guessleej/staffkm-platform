# Embeddable Chat Widget

> v2.4-A — 一行 `<script>` 把 staffKM 應用嵌任何網站。
> 適合：員工 portal / 公司官網 / 客戶服務頁。

## 前置

1. 建一個應用（[04-create-app.md](./04-create-app.md)）
2. 把它設為 **公開**（App 卡片 → 分享 → 切 `is_public=true`）
3. 拿到 App UUID（看分享 URL `/share/{appId}` 末段）

## 最小 snippet

把以下貼進 target 網站 `<body>`（或 `</body>` 前）：

```html
<script src="https://staffkm.example.com/widget.js"
        data-app-id="00000000-0000-0000-0000-000000000000"
        defer></script>
```

右下角會出現浮動按鈕「有問題嗎？」，點開 380×600 iframe，跑你的 App。

## 全部選項

| 屬性 | 必填 | 預設 | 說明 |
|---|---|---|---|
| `data-app-id` | ✅ | — | public App UUID |
| `data-host` | | script src origin | staffKM domain |
| `data-position` | | `bottom-right` | `bottom-right` / `bottom-left` |
| `data-color` | | `#4f46e5` | launcher 底色（任意 CSS color） |
| `data-label` | | `有問題嗎？` | launcher 文字 |

## 公開 API（給網站開發者）

`window.staffKM` 暴露：
```js
staffKM.open()    // 開
staffKM.close()   // 關
staffKM.toggle()  // 切
```

例：點某按鈕呼叫
```html
<button onclick="staffKM.open()">客服</button>
```

## 行為

- **第一次點才下載 iframe**（lazy mount）
- **ESC** 關
- **點空白處** 關（點 iframe 內 / launcher 不會關）
- **手機 RWD** — 寬度 < 480px 時 iframe 變 calc(100vw - 24px) × 75vh

## 安全

- staffKM `/share/{appId}` 走 `Content-Security-Policy: frame-ancestors *;` 允許 iframe
- `X-Frame-Options` 從 `SAMEORIGIN` 拿掉
- 但只有 `is_public=true` 的應用才回 200；其他一律 404
- iframe 用 `sandbox="allow-scripts allow-same-origin"`

## Demo 頁

在你 staffKM 部署上開：
```
https://staffkm.example.com/widget-demo.html
```

可以即時試 app-id / color / label，看 widget 行為。

## 卸載

要把 widget 從某頁面拔掉：
```js
['__staffkm-w-launcher','__staffkm-w-frame','__staffkm-w-style'].forEach(id => {
  document.getElementById(id)?.remove()
})
window.__staffkmWidgetMounted = false
```

---

下一篇：[08-admin.md](./08-admin.md)
