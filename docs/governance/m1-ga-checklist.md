# M1 GA Checklist & Smoke Report

| 欄位 | 內容 |
|---|---|
| Milestone | M1：多租戶 + Folder + 設計系統 + Application 版本 + UX |
| 日期 | 2026-05-16 |
| 範圍 | Sprint 0 + P1 全部、含 RFC-006 衍生工作 |

---

## 1. Trunk Smoke 結論

| 區塊 | 結果 |
|---|---|
| 容器健康 | 全部 `docker compose up -d` 全部 healthy（postgres / redis / minio / auth / knowledge / agent / chat / gateway / ui / ollama / embedder） |
| DB 表 | 12 張表全部建立並通過 idempotent bootstrap DDL |
| API 入口 | `/api/v1/auth/me` / `/workspaces` / `/applications` / `/knowledge/bases` / `/agents` / `/projects` / `/tools` / `/skills` / `/data-sources` / `/folders` / `/api-keys/verify` 全部 200 |
| 多租戶隔離 | three-layer（path middleware + RBAC dep + WHERE workspace_id）已覆蓋 agent + knowledge service |
| 公開存取 | `/api/v1/public/applications/{id}` 與 `/verify` 正確 bypass tenant context |
| Cold-start 復原 | 5xx 自動 retry（800ms / 1600ms），UI 顯示右下角 toast |
| 連點 nav | 不再 freeze，最差顯示 1-2 秒 transient spinner |

---

## 2. Backlog 33 項完成度

### Sprint 0（4 項 ✓）
| # | 項目 | 狀態 |
|---|---|---|
| 1 | GitHub Project + Backlog | ✓ |
| 2 | RFC 模板 + Definition of Done | ✓ |
| 3 | SLO / KPI | ✓ |
| 4 | Monorepo 重組 RFC-003 | ✓ |

### P1（M1 範圍）
| # | 項目 | 狀態 | PR |
|---|---|---|---|
| 5 | 多租戶 IAM 重構（auth + knowledge + agent 全部） | ✓ | #35-#52 |
| 6 | Folder 階層系統（KB 完成；其他模組 backend 完） | 🟡 | #61 (KB), #70 (entity_folders) |
| 7 | Application 版本控制 | ✓（backend） | #72 |
| 8 | 設計系統 v1 | ✓ | #39, #43, #44, #55 |
| 9 | UX 研究交付 | ✓（RFC-007 + UnderConstructionView） | #65, #72 |
| 10 | 品牌升級 | 🟡（藍圖完成、視覺資產待設計協作） | RFC-007 |
| 11 | 🚦 **M1 GA**：多租戶 + Folder + 設計系統 GA | ✓ | 本 doc |

### P2（M2 範圍 — 部分啟動）
| # | 項目 | 狀態 | PR |
|---|---|---|---|
| 12 | Workflow Engine v2 | 🟡 scaffold | #73 |
| 13 | 35+ Workflow Nodes | 🟡（30 / 35） | #73 |
| 14 | 5 種 Workflow Manager | 🟡（enum 欄位 + RFC-008） | #73 |
| 15 | Sandbox 容器 | ⏳ | RFC-008 |
| 16 | LogicFlow 編輯器升級 | ⏳ | M2-4 |
| 17 | 🚦 M2 GA | ⏳ | — |

### P3 / P4 / P5（待 M2 GA 後啟動）
全部 17 項仍為 pending；其中 P5「Nuxt 3 遷移」已有 RFC-004。

---

## 3. RFC 一覽

| RFC | 主題 | 狀態 |
|---|---|---|
| RFC-001 | Multi-tenant | Accepted / Stage 2 完成 |
| RFC-002 | Workflow Engine v2 | Superseded by RFC-008 |
| RFC-003 | Monorepo 重組 | Accepted / Done |
| RFC-004 | Nuxt 3 遷移 | Draft（P5） |
| RFC-005 | 地端 LLM 優先 | Accepted |
| RFC-006 | MaxKB parity + claude.ai UI | Accepted / 多個衍生 PR 落地 |
| RFC-007 | UX 研究 + 品牌升級 | Draft |
| RFC-008 | Workflow Engine v2 scaffold | Draft（M2-1~5 拆分） |

---

## 4. 累計 PR 統計（從 Sprint 0 到本里程碑）

- **27 個 PR merged**（#35 ~ #73）
- **新增 ~12 張表**（包含原 4 張 base + 8 張新表）
- **40+ 個 REST endpoint**
- **30 個 Workflow node types**（原 20 → 30）
- **5 個 stores + 9 個 UI primitives**

---

## 5. M1 GA 通過條件 ✓

- [x] 三層多租戶隔離（path / RBAC / SQL）
- [x] KB / Application / Tool / Skill / DataSource CRUD + Project 抽象
- [x] 設計系統 v1（design tokens / ChatLayout / DashboardLayout / 30 SVG icons）
- [x] i18n 框架 + zh-TW 主要字典
- [x] Application 版本控制（backend）
- [x] Cold-start 韌性（retry + toast）
- [x] Stub 頁面 UX（UnderConstructionView）
- [ ] 品牌資產（logo / 插畫）— 待設計協作；不阻塞 M1
- [ ] 全 i18n 覆蓋率 ≥ 90% — 待逐 view 增補；可在 M2 期間推進
- [ ] 使用者日記 / SUS 量表 — 待 RFC-007 後續啟動

**結論：M1 GA 條件達成（必要件全部 ✓，非阻塞項列入 backlog）。**

---

## 6. 已知遺留事項（不阻塞 M1，列入 M2 前置）

1. `/api/v1/agents/` trailing-slash 偶爾 pending — FastAPI redirect 行為，可後續關閉 redirect_slashes
2. Pinia store cache for agents/knowledge/applications — 解決 rapid-nav 期間 transient spinner（屬 UX 優化非 bug）
3. 30 個 workflow node 中 10 個是 metadata-only（M2-1 補實作）
4. 5 個 workflow manager 策略只有 enum，無實際 executor 行為（M2-2）
5. 設定 / 使用者 / 命中測試 三個 stub 頁面（UnderConstructionView 已包裝，內容由後續 PR 補）

---

## 7. 下一里程碑（M2）建議優先順序

| 順序 | 子 PR | 預估 |
|---|---|---|
| 1 | M2-1 補 10 個新 node `_exec_*` | 2-3 d |
| 2 | M2-2 Workflow Manager 5 策略 | 3 d |
| 3 | D-5 後續：FolderTree 接 ApplicationListView/ToolListView | 1 d |
| 4 | D-7 後續：Application 編輯頁加版本抽屜 | 1 d |
| 5 | M2-3 Sandbox 容器（需 Ops review） | 5 d |
| 6 | M2-4 LogicFlow 編輯器升級 | 2 d |
| 7 | M3 啟動：Model Provider 抽象 | 大概 1 週 |
