# SLO / KPI — staffKM v2

> Service Level Objectives 與 Key Performance Indicators 是團隊「品質契約」。沒達標就停發新功能、修品質。

---

## 1. SLI / SLO 對照表

| 服務 | SLI（指標） | SLO（目標） | 量測窗口 | 違反處置 |
|------|-------------|-------------|----------|----------|
| **API Gateway** | 成功回應率（HTTP < 500） | ≥ 99.5% | 過去 28 天 | 觸發 P1 incident |
| **API Gateway** | latency p95 | < 500 ms | 過去 28 天 | 觸發 P2 incident |
| **API Gateway** | latency p99 | < 1500 ms | 過去 28 天 | 進入 follow-up |
| **Knowledge** | 文件處理成功率 | ≥ 99% | 過去 7 天 | retry policy 檢視 |
| **Knowledge** | embedding latency p95 | < 2 s / 段落 | 過去 7 天 | 模型 / 資源檢視 |
| **Knowledge** | hybrid search p95 | < 800 ms | 過去 7 天 | 索引 / SQL 優化 |
| **Workflow** | 執行成功率 | ≥ 99% | 過去 7 天 | DAG bug 排查 |
| **Workflow** | 執行 latency p95 | < 5 s（不含 LLM） | 過去 7 天 | engine 優化 |
| **Agent (LLM stream)** | TTFT（time to first token） p95 | < 2 s | 過去 7 天 | provider / network |
| **Auth** | 登入 latency p95 | < 300 ms | 過去 7 天 | DB / cache |
| **整體 platform** | 月可用性 | ≥ 99.5% | 月 | post-mortem |

> **Error Budget**：99.5% 月可用性 = 每月最多 3.6 小時 downtime。用完則凍結 release。

---

## 2. KPI（產品 / 商業）

| 類別 | KPI | 目標 (Q1) | 目標 (Q2) |
|------|-----|-----------|-----------|
| **採用** | 月活躍 workspace 數 | 50 | 200 |
| **採用** | 應用建立數 / workspace | 3 | 10 |
| **互動** | 月對話數 | 5,000 | 50,000 |
| **品質** | RAG 命中率（人工 sample） | ≥ 80% | ≥ 88% |
| **品質** | 用戶正向回饋率（thumbs up） | ≥ 75% | ≥ 85% |
| **效率** | 平均文件入庫時間 | < 60 s/MB | < 30 s/MB |
| **成本** | 月平均 token 成本 / workspace | 觀察 | < 預算的 80% |
| **品牌** | GitHub stars | 200 | 1000 |
| **品牌** | 社群 PR 貢獻者 | 5 | 20 |

---

## 3. 量測來源

| 指標類別 | 工具 | 採樣方式 |
|---------|------|----------|
| API latency / 成功率 | Prometheus（FastAPI middleware） | 每秒抓取 |
| 業務事件 | 結構化 log → Loki | 即時 push |
| 分散式追蹤 | OpenTelemetry → Tempo | 採樣 10% |
| 用戶行為 | 自架 PostHog 或 Plausible | 全量 |
| 模型用量 | `model_usage_log` 表 | 每次呼叫 |
| RAG 品質 | 每週手動評估 100 題 | 人工標註 |

---

## 4. 警示分級

| Severity | 例子 | 通知 | 回應時間 |
|----------|------|------|----------|
| **P1（緊急）** | 全站 down、login 失敗 > 5% | PagerDuty + 電話 | 15 分鐘 |
| **P2（嚴重）** | 單服務 SLO 違反、p95 暴增 5× | Slack #oncall | 1 小時 |
| **P3（觀察）** | 單一 endpoint 異常、預警 budget 80% | Slack #monitoring | 工作日內 |
| **P4（注意）** | 套件更新、深夜批次失敗 | Email digest | 下個 sprint |

---

## 5. SLO 違反流程

```
警示 → 確認 incident → 啟動 incident commander
   → 緩解（rollback / scale up / hotfix）
   → 解除警示
   → 48h 內完成 post-mortem（無責文化）
   → 把 action items 進 backlog
```

每月底 PMP review：
- 違反次數
- Error budget 使用率
- 改善 action 完成率
- 是否需要調整 SLO

---

## 6. 修訂紀錄

| 版本 | 日期 | 修訂者 | 內容 |
|------|------|--------|------|
| 1.0 | 2026-05-15 | PMP + 架構師 | 初版（Sprint 0 凍結） |
