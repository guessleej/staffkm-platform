# staffKM v2 文件中心

> 以 PMP / 架構師視角組織的專案治理文件。所有重大決策、SLO、風險、流程皆在此追蹤。

## 📁 目錄結構

```
docs/
├── rfc/                    # 設計提案（每個重大改動先寫 RFC）
│   ├── RFC-TEMPLATE.md
│   ├── RFC-001-multi-tenant.md
│   ├── RFC-002-workflow-engine-v2.md
│   ├── RFC-003-monorepo-structure.md
│   └── RFC-004-nuxt-migration.md
├── governance/             # 專案治理
│   ├── slo.md              # SLO / KPI 定義
│   ├── definition-of-done.md
│   ├── coding-standards.md
│   └── risk-register.md
├── adr/                    # Architecture Decision Records（既成決策）
│   └── (空，由 RFC 通過後遷入)
└── runbooks/               # 維運手冊
    └── (incident response, on-call playbook…)
```

## 🔄 設計決策流程（RFC → ADR）

```
   提案者                 reviewers              merge
     │                       │                   │
     ▼                       ▼                   ▼
1. 寫 RFC ──→ 2. 開 PR ──→ 3. 至少 2 名 reviewer 通過
                                    │
                                    ▼
                          4. 加 status: Accepted
                                    │
                                    ▼
                          5. 移至 docs/adr/（不可變歷史）
```

## 📊 治理節奏

| 節奏 | 時段 | 內容 |
|------|------|------|
| Daily Standup | 每日 09:30 (10 分鐘) | yesterday/today/blockers |
| Sprint Planning | 雙週四 10:00 (60 分鐘) | 未來 2 週 commit |
| Sprint Review | 雙週四 15:00 (60 分鐘) | demo + retro |
| RFC Review | 每週三 14:00 (30 分鐘) | 開放 RFC 討論 |
| Stakeholder Demo | 每月最後週五 (60 分鐘) | 對外展示 |

## 📌 重要連結

- 專案 Backlog：GitHub Project『staffKM v2』
- 設計稿：Figma 專案『staffKM v2』
- 監控：http://grafana.staffkm.local
- 文件站（規劃中）：https://docs.staffkm.io
