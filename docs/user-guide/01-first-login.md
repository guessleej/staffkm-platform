# 第一次登入

## 1. 開首頁

打開 `https://staffkm.example.com`，會看到登入頁：

- 左側：staffKM 品牌視覺
- 右側：登入表單

## 2. 登入

| 模式 | 操作 |
|------|------|
| 帳號密碼 | 填工號 / 密碼 → 「登入系統」|
| SSO（OIDC，若 admin 啟用）| 點「使用 Google 登入」按鈕（標籤依 IdP 而定）|
| LDAP（若 admin 啟用） | 用 AD 帳號直接登（後端自動比對）|

**密碼錯 3 次** 會出現數學驗證碼，答對才能繼續。

## 3. 第一次自動跳「歡迎導覽」

3 個步驟，30 秒看完：

1. **歡迎** — 看 staffKM 能做什麼
2. **挑路徑** — 「從模板」（推薦）/「空白應用」
3. **建知識庫** — KB 4 步教學 + 「去建知識庫」按鈕

「我熟了直接進去」隨時可跳。下次不會再跑（除非清 localStorage / settings menu 「重看導覽」）。

## 4. 選好路徑後跳到哪？

| 選 | 跳哪 |
|---|---|
| ✨ 從模板 | `/applications` + 模板畫廊自動開 |
| ⚡ 空白應用 | `/applications` + 建立 dialog 自動開 |
| 完成導覽 | `/applications` 主畫面 |
| 去建知識庫 | `/knowledge` |

## 5. 跳過導覽後想再看

進右上「設定」menu →「重看導覽」（待加）。或 DevTools：
```js
localStorage.removeItem('staffkm.onboarding.done'); location.reload()
```

## 6. 切換語言

右上角 locale selector：繁體中文 / 简体中文 / English。
切換後 localStorage 記住，下次 auto-apply。

## 7. 切換主題

右上 sun / moon 按鈕 — light / dark mode flip。
偵測 `prefers-color-scheme` 預設。

---

下一篇：[02-chat.md](./02-chat.md) — 跟 AI 對話 + 看引用 + 展開 artifact
