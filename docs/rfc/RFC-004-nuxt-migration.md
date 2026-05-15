# RFC-004: 前端從 Vite + Vue 3 升級為 Nuxt 3

| 欄位 | 內容 |
|------|------|
| 編號 | RFC-004 |
| 提案者 | @lead-fe |
| 狀態 | Draft |
| 建立日期 | 2026-05-15 |
| Reviewers | @architect @ux @pmp |
| 相關 | RFC-003 (monorepo) |

---

## 1. 摘要

把 `apps/web` 從 Vite + Vue 3 SPA 升級為 **Nuxt 3 + Nitro**。獲得 SSR / SEO、file-based routing、auto-imports、server routes（BFF 模式）、image optimization、i18n module 等開箱即用能力。對 LogicFlow 編輯器這類重客戶端的頁面用 client-only 包裝。

## 2. 動機

現況痛點：
- SPA 首屏白畫面 1.5s（測量 LCP）
- 公開分享頁（`/share/:appId`）對 SEO 不友善（搜尋引擎抓不到）
- 路由都手寫在 `router/index.ts`，新增頁面要改三處
- 沒有 BFF 層，前端直接打多個微服務（CORS / token 散亂）
- 沒有 i18n module，自己拼 vue-i18n
- 沒有圖片優化（headshot 直接 1MB）

Nuxt 3 解決全部這些，且保留 Vue 3 + Vite 的開發體驗。

## 3. 目標與非目標

**目標**
- [ ] G1：所有頁面遷至 `pages/` file-based routing
- [ ] G2：公開頁 SSR（`/share/[appId]`、landing page、docs）
- [ ] G3：登入後頁面用 SPA mode（避免 SSR 認證複雜化）
- [ ] G4：Nuxt server routes 當 BFF 統一打後端微服務
- [ ] G5：i18n（`@nuxtjs/i18n` module）支援 zh-TW / zh-CN / en / ja
- [ ] G6：Image module（自動 webp、lazy load）
- [ ] G7：Color mode module（dark mode）
- [ ] G8：Pinia 沿用（Nuxt 有 `@pinia/nuxt` module）
- [ ] G9：LogicFlow 編輯器用 `<ClientOnly>` 包裝，不破壞 SSR

**非目標**
- N1：不上 Nuxt UI Pro（付費），用自家 ui-kit
- N2：不用 Nuxt Content（docs 用 Docusaurus）
- N3：不做 hybrid rendering 細調（先用 route rules 簡單分）

## 4. 提案設計

### 4.1 技術選型

| 用途 | 套件 |
|------|------|
| Framework | Nuxt 3.14+ |
| State | Pinia (`@pinia/nuxt`) |
| UI | Tailwind CSS (`@nuxtjs/tailwindcss`) + 自家 ui-kit |
| i18n | `@nuxtjs/i18n` |
| Auth | 自寫 middleware + Pinia store（沿用現有 token 流程） |
| Color mode | `@nuxtjs/color-mode` |
| Image | `@nuxt/image` |
| Icons | `@nuxt/icon` (Iconify) |
| Form | `vee-validate` + `zod` |
| Markdown | `mdc` 或 `marked` |
| Diagram (workflow) | LogicFlow（client-only） |
| API client | `$fetch`（Nuxt 內建）+ 自動產生的 SDK |

### 4.2 目錄結構

```
apps/web/
├── pages/                  # file-based routing
│   ├── index.vue
│   ├── login.vue
│   ├── share/[appId].vue                    # 公開分享頁（SSR）
│   ├── workspace/[wsId]/
│   │   ├── index.vue                        # workspace 首頁
│   │   ├── chat.vue
│   │   ├── knowledge/
│   │   │   ├── index.vue
│   │   │   └── [kbId]/
│   │   │       ├── documents.vue
│   │   │       └── hit-test.vue
│   │   └── applications/
│   │       ├── index.vue
│   │       └── [appId]/
│   │           ├── chat.vue
│   │           └── workflow.vue
│   └── admin/...
├── layouts/
│   ├── default.vue        # dashboard 三欄
│   ├── public.vue         # 公開頁
│   └── auth.vue           # 登入畫面
├── components/
│   ├── workflow/
│   ├── chat/
│   ├── knowledge/
│   └── ui/                # 從 packages/ts/ui-kit 載入或本地
├── composables/
│   ├── useAuth.ts
│   ├── useWorkspace.ts
│   └── useApi.ts
├── middleware/
│   ├── auth.ts            # 全站登入檢查
│   └── workspace.ts       # 確認 wsId 有效
├── server/                # Nuxt server routes（BFF）
│   ├── api/
│   │   ├── proxy/[...].ts # 對後端微服務代理
│   │   └── upload.ts      # 大檔案串流
│   └── middleware/
│       └── inject-trace.ts
├── stores/                # Pinia
│   ├── auth.ts
│   ├── workspace.ts
│   └── conversation.ts
├── plugins/
│   ├── api.ts
│   └── error-handler.ts
├── i18n/
│   ├── zh-TW.json
│   ├── zh-CN.json
│   ├── en.json
│   └── ja.json
├── public/                # 靜態檔
├── nuxt.config.ts
├── tailwind.config.ts
└── tsconfig.json
```

### 4.3 nuxt.config.ts 雛形

```typescript
export default defineNuxtConfig({
  modules: [
    '@nuxtjs/tailwindcss',
    '@pinia/nuxt',
    '@nuxtjs/i18n',
    '@nuxtjs/color-mode',
    '@nuxt/image',
    '@nuxt/icon',
    '@vueuse/nuxt',
  ],

  // hybrid rendering：公開頁 SSR、登入後 SPA
  routeRules: {
    '/share/**': { ssr: true, headers: { 'cache-control': 's-maxage=60' } },
    '/workspace/**': { ssr: false },     // SPA
    '/admin/**':     { ssr: false },
    '/login':        { ssr: false },
    '/':             { ssr: true, prerender: true },  // landing
  },

  i18n: {
    locales: ['zh-TW', 'zh-CN', 'en', 'ja'],
    defaultLocale: 'zh-TW',
    strategy: 'no_prefix',
  },

  colorMode: { classSuffix: '' },

  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || '/api/v1',
    },
  },

  nitro: {
    devProxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
```

### 4.4 LogicFlow 整合（client-only）

```vue
<!-- pages/workspace/[wsId]/applications/[appId]/workflow.vue -->
<template>
  <NuxtLayout name="default">
    <ClientOnly>
      <WorkflowEditor :app-id="appId" />
      <template #fallback>
        <div class="flex h-full items-center justify-center">
          載入工作流編輯器…
        </div>
      </template>
    </ClientOnly>
  </NuxtLayout>
</template>
```

LogicFlow 是大型 client-only 套件，不能 SSR。用 `<ClientOnly>` + `definePageMeta({ ssr: false })` 雙保險。

### 4.5 i18n 範例

```vue
<template>
  <button>{{ $t('button.upload') }}</button>
</template>
```

```json
// i18n/zh-TW.json
{
  "button": {
    "upload": "上傳文件"
  }
}
```

### 4.6 BFF（Nuxt Server Routes）

```typescript
// server/api/proxy/[...].ts
export default defineEventHandler(async (event) => {
  const path = getRouterParam(event, '_')
  const config = useRuntimeConfig()
  const token = getCookie(event, 'access_token')

  return await $fetch(`${config.apiBase}/${path}`, {
    method: getMethod(event),
    headers: { Authorization: `Bearer ${token}` },
    body: await readBody(event).catch(() => undefined),
  })
})
```

好處：
- token 走 httpOnly cookie，前端 JS 拿不到（XSS 防禦強）
- 多服務聚合在 server 層
- log / metric / trace 可在 BFF 層集中

## 5. 替代方案

| 方案 | 優點 | 缺點 | 為何不選 |
|------|------|------|----------|
| 維持 Vite SPA | 不用搬 | 痛點不解 | 違反 G1-G7 |
| Next.js（換成 React） | 生態大 | 整套換語言、所有元件重寫 | 成本爆炸 |
| Astro + Vue islands | SSG 快 | 互動性弱、不適合 dashboard | 不對需求 |
| **Nuxt 3（本案）** | **Vue 原生升級、模組豐富** | 學習 Nitro、SSR debug 麻煩 | **採用** |

## 6. 風險與緩解

| 風險 | 機率 | 衝擊 | 緩解 |
|------|------|------|------|
| LogicFlow 在 Nuxt 環境 hydration 錯誤 | 中 | 高 | 強制 client-only，POC 先驗證 |
| SSR 環境下 localStorage 取不到（auth） | 高 | 中 | 用 cookie + middleware；POC 階段先解決 |
| 既有 Vue 組件 import 路徑全壞 | 確定 | 中 | auto-import 新規則 + sed 過渡 |
| 部署檔結構從 dist 變 .output | 確定 | 中 | nginx serve 改寫；docker image 重建 |
| Bundle 變大 | 中 | 中 | route-level code splitting + tree-shake check |

## 7. 影響範圍

- **檔案**：`ui/` 全部重組為 `apps/web/`，約 30+ Vue 組件 + 8 路由要遷
- **建置**：Vite → Nitro，dist → .output；Dockerfile 重寫
- **部署**：nginx serve 規則調整；新增 `/api/proxy/*` route
- **效能**：FCP 預期改善 50%+（SSR 公開頁）；bundle 增 ~30KB（Nitro overhead）

## 8. 推出計畫（5 週）

- [ ] **W1**：POC — 起新 Nuxt 專案，遷 1 頁（login）+ LogicFlow 試打
- [ ] **W2**：把 layout / store / api client 遷過去
- [ ] **W3-W4**：頁面逐一遷移（每天 2-3 頁），舊 SPA 並存
- [ ] **W5**：i18n / dark mode / image 模組整合；舊 SPA 下線
- [ ] feature flag：`NUXT_ROLLOUT=true` 切換 nginx 路由

回滾：nginx 一行設定切回舊 dist；舊 SPA 保留 1 個月。

## 9. 量測指標

- LCP：< 1.0s（公開頁，SSR）
- TTI：< 2.5s（dashboard 頁）
- bundle size：< 350KB（gzip）
- Lighthouse：Performance ≥ 90、SEO ≥ 95
- i18n 覆蓋率：100%

## 10. 開放問題

- [ ] Q1：LogicFlow 要不要找 Vue 3 native 替代品（如 vue-flow）？@lead-fe POC
- [ ] Q2：要不要直接用 Nuxt UI（Tailwind 元件）省自家 ui-kit 工作？@ux 評估
- [ ] Q3：i18n key 命名規範？flat / nested？@ux 訂

## 11. 參考資料

- [Nuxt 3 docs](https://nuxt.com/docs)
- [Nitro server engine](https://nitro.unjs.io/)
- 相關：RFC-003 (monorepo)
