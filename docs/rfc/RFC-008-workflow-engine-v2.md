# RFC-008：Workflow Engine v2 啟動藍圖

| 欄位 | 內容 |
|---|---|
| 編號 | RFC-008 |
| 提案者 | @leeweiye |
| 狀態 | Draft |
| 建立日期 | 2026-05-16 |
| 取代 / 被取代 | 無（後續 PR 取代 RFC-002 部分章節） |

---

## 1. 摘要
本 RFC 為 Workflow Engine v2 的 scaffolding 起點。本次 PR 交付：版本控制 (snapshot+restore)、10 個新節點 metadata、5 種 Manager 策略 enum、Sandbox 規劃。實際 executor 行為與 sandbox 容器整合分多個後續 PR 推進。

## 2. 本 PR 已交付
- **DDL**：`workflow_versions` 表（per-application snapshot of nodes+edges）
- **API**：`POST/GET/restore` workflow versions endpoints
- **applications.workflow_manager** 欄位（enum：simple / parallel / retry / batch / sandbox）
- **lf-nodes.ts**：原 20 節點 → 30 節點（新增 wait / switch / map / reduce / webhook / notify / email / schedule / transform / merge）
- **Palette groups**：加「進階流程控制」、「觸發」兩組

## 3. Workflow Manager 策略（applications.workflow_manager）

| 策略 | 行為 |
|---|---|
| `simple` | 預設；單執行緒、無 retry |
| `parallel` | branch node 可平行執行（asyncio.gather） |
| `retry` | 節點失敗時依 config.retry_policy 重試（指數退避） |
| `batch` | list 變數自動 split 為多個任務並行 |
| `sandbox` | 在隔離容器執行可信度低的 node（M2 後期） |

本 PR 只加 enum 欄位；executor 行為由後續 PR 補。

## 4. Sandbox 設計方向（M2 後期）

- 用 gVisor 或 nsjail 隔離 shell / custom Tool 執行
- 限制 CPU / 記憶體 / 網路 ACL
- 透過 RPC 把 nodes 序列化丟進 sandbox
- 結果 timeout 強制終止

不在本 PR 範圍；屬獨立 PR 並需 Ops review。

## 5. 後續 PR 拆分

| 子 PR | 內容 | 工作量 |
|---|---|---|
| M2-1 | 新 10 節點的 `_exec_*` 方法（基本版） | 2-3 天 |
| M2-2 | Workflow Manager 5 策略 executor 行為 | 3 天 |
| M2-3 | Sandbox 容器整合（gVisor / nsjail） | 5 天 + Ops |
| M2-4 | LogicFlow 編輯器升級（mini-map、複製貼上、群組） | 2 天 |
| M2-5 | Workflow 樣板市集（與 D-1 Tool 市集同框架） | 3 天 |

## 6. 評估指標
- 30+ 節點覆蓋率 ≥ 80%（24 / 30 有實作）
- 同一 workflow snapshot → restore 後行為 100% 一致
- Sandbox 啟動延遲 < 500ms

## 7. 不在本 RFC 範圍
- 實際 sandbox runtime
- 35+ 完整節點細部實作
- 跨 workflow 觸發（webhook 互呼）
