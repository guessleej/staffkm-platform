# Risk Register — staffKM v2

> 風險登記簿，每週 PMP review。新增風險用 PR + 標 `type:risk`。已實現風險記錄處置結果並轉 lessons-learned。

**判讀**
- **機率**：高（>50%）/ 中（20–50%）/ 低（<20%）
- **衝擊**：高（影響里程碑）/ 中（拖慢 1 sprint）/ 低（局部）
- **狀態**：🟢 監控中 / 🟡 已觸發處理中 / 🔴 已實現待 post-mortem / ⚫ 已關閉

---

## 1. 技術風險

| ID | 風險 | 機率 | 衝擊 | 緩解策略 | 負責 | 狀態 |
|----|------|------|------|----------|------|------|
| TR-01 | Multi-tenant migration 破壞舊資料 | 中 | 高 | Reversible Alembic + dry-run + 完整備份；建立 default workspace 收容舊資料 | 架構師 | 🟢 |
| TR-02 | Workflow DAG 死鎖 / 無限遞迴 | 中 | 高 | 入庫前 NetworkX cycle 檢測；執行 timeout 30s；sub-workflow 深度 ≤ 5 | 架構師 | 🟢 |
| TR-03 | 模型推論成本失控（OpenAI bill 超支） | 高 | 中 | Token quota + rate limit middleware；月度預警 80%；硬上限 cut-off | 後端 | 🟢 |
| TR-04 | 35 節點品質參差不齊 | 高 | 中 | 每節點必須 unit test + E2E；BaseNodeView 抽象覆蓋 80% 共通邏輯 | 後端 | 🟢 |
| TR-05 | 20 家 provider 維護成本 | 中 | 中 | 用 LiteLLM proxy 統一介面；自家只維護抽象層；社群 PR welcome | 架構師 | 🟢 |
| TR-06 | Embedding 維度遷移破壞既有向量 | 中 | 高 | Bootstrap DDL 自動偵測 + 提示 truncate；雙寫過渡期 | 後端 | 🟢 |
| TR-07 | LogicFlow + Nuxt 3 SSR hydration 衝突 | 高 | 中 | 強制 `<ClientOnly>`；POC 階段先驗證；備案 vue-flow | 前端 | 🟢 |
| TR-08 | Sandbox 容器逃逸（user code RCE） | 低 | 致命 | gVisor / Firecracker 強隔離；限制 CPU/RAM/網路；audit log 全紀錄 | 架構師 + DevOps | 🟢 |
| TR-09 | Trace 表暴量影響查詢效能 | 高 | 中 | 按月 partition；保留 90 天；冷資料移 S3 | 架構師 | 🟢 |
| TR-10 | OpenAPI codegen 與後端 schema 漂移 | 中 | 低 | CI 強制 `git diff` = 0；pre-commit hook 自動 regen | 後端 + 前端 | 🟢 |

## 2. 安全風險

| ID | 風險 | 機率 | 衝擊 | 緩解策略 | 負責 | 狀態 |
|----|------|------|------|----------|------|------|
| SR-01 | API key 洩漏（log / response） | 低 | 高 | Vault 集中管理；前端永不回傳明文；audit log；gitleaks CI | 架構師 | 🟢 |
| SR-02 | 跨 workspace 資料外洩 | 中 | 致命 | scoped query helper 強制；lint rule 禁直接 ORM；E2E 跨租戶斷言 | 架構師 | 🟢 |
| SR-03 | SQL injection（raw SQL 多） | 中 | 高 | 一律 parameterized；PR review checklist；SAST（bandit） | 後端 | 🟢 |
| SR-04 | XSS（Markdown / 用戶內容） | 中 | 中 | DOMPurify；CSP；marked safe mode | 前端 | 🟢 |
| SR-05 | MCP 工具被惡意 prompt 觸發 | 中 | 高 | 工具白名單 + 二次確認 UI；危險操作 dry-run | 架構師 | 🟢 |
| SR-06 | Public share link 被搜尋引擎索引機敏內容 | 中 | 中 | 預設 noindex；明確開關；token 化 URL | 後端 + 前端 | 🟢 |
| SR-07 | 上傳檔案執行（Office macro / SVG XSS） | 中 | 中 | 黑名單副檔名；Content-Type sniff；隔離 bucket | 後端 | 🟢 |

## 3. 專案 / 流程風險

| ID | 風險 | 機率 | 衝擊 | 緩解策略 | 負責 | 狀態 |
|----|------|------|------|----------|------|------|
| PR-01 | Scope creep（停不下來補功能） | 高 | 高 | 每 Sprint RICE 排序、最多 4 項；PR 凍結期；新需求進 backlog 排隊 | PMP | 🟢 |
| PR-02 | 關鍵成員離職 / 病假 | 中 | 高 | 雙人 ownership；文件齊全；onboarding < 1 天 | PMP | 🟢 |
| PR-03 | Sprint commitment 無法達成 | 高 | 中 | velocity 追蹤；下 sprint 自動扣 20% buffer | PMP | 🟢 |
| PR-04 | RFC review 無人回應卡關 | 中 | 中 | 每週固定 RFC review 會議；72h 無回應視同同意 | PMP | 🟢 |
| PR-05 | 設計稿落後開發 | 高 | 中 | UX 領先 1 sprint 完工；pair design review | UX + PMP | 🟢 |
| PR-06 | Stakeholder 期望不一致 | 中 | 高 | 月度 demo + roadmap 公開；OKR 對齊 | PMP | 🟢 |

## 4. 維運 / 商業風險

| ID | 風險 | 機率 | 衝擊 | 緩解策略 | 負責 | 狀態 |
|----|------|------|------|----------|------|------|
| OR-01 | Production downtime（單點失效） | 中 | 高 | K8s 多 replica；DB streaming replica；MinIO replication | DevOps | 🟢 |
| OR-02 | 備份失效 / 無法 restore | 低 | 致命 | 每週實測 restore；異地備份 | DevOps | 🟢 |
| OR-03 | 雲端成本超預算 | 中 | 中 | 月度成本 dashboard；budget alert；reserved instance | DevOps + PMP | 🟢 |
| OR-04 | 開源社群冷淡（GH stars < 預期） | 中 | 中 | marketing site；技術部落格；conference talk | PMP + 美工 | 🟢 |
| OR-05 | MaxKB / Dify 推出更強功能 | 高 | 中 | 競品季度追蹤；快速跟進關鍵差異 | 架構師 + PMP | 🟢 |

---

## 5. 風險矩陣（視覺化）

```
              低機率              中機率              高機率
高衝擊  │  TR-08, OR-02   │  TR-01, TR-02,    │  PR-01, PR-06
        │  SR-01          │  SR-02, OR-01     │  TR-08(*)
        │                 │  PR-02, PR-06     │
─────── ┼───────────────── ┼───────────────────┼──────────────────
中衝擊  │                 │  TR-03, TR-05,    │  TR-04, TR-07,
        │                 │  TR-09, SR-03,    │  PR-03, PR-05,
        │                 │  SR-05, SR-06,    │  OR-04, OR-05
        │                 │  OR-03, PR-04     │
─────── ┼───────────────── ┼───────────────────┼──────────────────
低衝擊  │  SR-04, SR-07,  │  TR-10            │
        │  PR-02(*)       │                   │
```

**重點關注區（高衝擊 + 中/高機率）**：
- 🚨 PR-01 Scope creep（高機率高衝擊）
- 🚨 SR-02 跨 workspace 資料外洩
- 🚨 TR-01 Multi-tenant migration
- 🚨 TR-02 Workflow DAG 死鎖

---

## 6. 變更紀錄

| 日期 | 變更人 | 內容 |
|------|--------|------|
| 2026-05-15 | PMP + 架構師 | 初版（Sprint 0 凍結，27 項風險） |
