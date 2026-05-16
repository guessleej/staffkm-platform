# staffKM Docs Site（VitePress）

> M5 GA：靜態文件站雛形。框架選 VitePress（與前端共用 Vue 生態；輕量、零 runtime）。

## 啟動

```bash
pnpm --filter @staffkm/docs dev      # localhost:5173
pnpm --filter @staffkm/docs build    # 出 .vitepress/dist
pnpm --filter @staffkm/docs preview
```

## 結構

```
apps/docs/
├── .vitepress/config.ts      # 站台設定（nav / sidebar / theme）
├── index.md                  # 首頁
├── user/                     # 終端使用者指南
│   ├── getting-started.md
│   ├── chat.md
│   └── workflows.md
├── admin/                    # 管理者
│   ├── installation.md
│   ├── multi-tenant.md
│   ├── quota.md
│   └── backup-dr.md
└── developer/                # 開發者
    ├── api.md
    ├── sdk-python.md
    ├── cli.md
    └── webhooks.md
```

## 部署

- Cloudflare Pages / Netlify / Vercel 任一靜態站平台
- CI 在 push main 時自動 build + deploy（M5 中段補）
