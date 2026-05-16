# staffKM Marketing Landing

純靜態 landing page。Vite dev server / build。

## 啟動

```bash
pnpm --filter @staffkm/marketing dev      # localhost:5173
pnpm --filter @staffkm/marketing build    # 出 dist/
pnpm --filter @staffkm/marketing preview
```

## 部署

`dist/` 丟 Cloudflare Pages / Netlify / Vercel 即可。CI 自動 deploy 留 M5 中段。

## 內容修改

- `index.html` — 內容
- `public/style.css` — 樣式（用品牌色 token；無依賴）
- `public/favicon.svg` — favicon（與主 app 一致）

## 不在這份範圍

- 互動 demo 嵌入頁面（v2.1 規劃）
- 文章 / blog（用 docs site 或外接 CMS）
- A/B testing（v2.x）
