# staffKM Marketing Site

Vue 3 SPA 行銷站 — Landing / Pricing / Cases / About。

跟 `apps/web/` 同 stack（Vite + Vue 3 + Vue Router + Tailwind），純前端、無 backend、無 DB。

## 啟動

```bash
pnpm --filter @staffkm/marketing install
pnpm --filter @staffkm/marketing dev        # localhost:5180
pnpm --filter @staffkm/marketing build      # → dist/
pnpm --filter @staffkm/marketing preview    # 預覽 dist/
```

## Routes

| Path | View | 用途 |
|------|------|------|
| `/` | HomeView | Landing：Hero / Features × 6 / How it works / Logos / CTA |
| `/pricing` | PricingView | 4 個 plan + 功能對比表 + FAQ × 5 |
| `/cases` | CasesView | 3 個 case study 列表 |
| `/cases/:slug` | CaseDetailView | 單一案例：challenge / solution / result / quote / metrics |
| `/about` | AboutView | 使命 / 原則 / 聯絡 |

## 內容修改

所有文案集中在 `src/data/`：

- `features.ts` — 6 個 feature highlights
- `pricing.ts` — 4 個 plan + 對比表 + FAQ
- `cases.ts` — 3 個 case study（中型科技 HR / 區域銀行 IT / 連鎖零售 onboarding）

組件層：`src/components/` (`MarketingNav` / `Footer` / `HeroSection` / `FeatureCard` / `CaseCard` / `PricingTable`)。

## CTA 連結

`登入` → `/login`，`免費試用` → `/signup`。
假設 marketing 與主 app 同 domain。如需 cross-domain，加 `VITE_APP_URL` env 並改 `MarketingNav.vue` / `HeroSection.vue`。

## Docker / compose 部署

infra/docker-compose.yml 提供 `marketing` service（profile `marketing`，nginx 靜態服務）：

```bash
# 1. 先 build 出 dist/
cd apps/marketing && pnpm build

# 2. 起 nginx 服務
cd ../../infra && docker compose --profile marketing up -d marketing
# → http://localhost:8081
```

> **注意**：compose service 是 volume mount `dist/`，因此每次內容修改需手動重新 `pnpm build`。
> Prod 由 Caddy reverse proxy（v4.3 整合）。

## 不在這份範圍（v4.x backlog）

- i18n（純 zh-TW；en / zh-CN 留 backlog）
- SSR / SSG（純 SPA，SEO 需求時再升 Astro / Nuxt）
- Headless CMS（內容寫進 `src/data/*.ts`）
- Contact form 後端（用 `mailto:`）
- Analytics（Plausible / Umami）
