# v2.0 → v2.1 Roadmap

> v2.0 GA 後的下一輪。範圍以「**收 v2.0 known limitations + M4 中段完成**」為主，
> 不引入新里程碑。預計 6~8 週。

## Pillar 1：M4 中段完成

| Item                                | 對應 RFC | 預估 |
| ----------------------------------- | -------- | ---- |
| trigger_worker dispatcher           | RFC-011  | M    |
| workflow `memory_save` / `memory_search` node | RFC-011 | M |
| workflow `mcp_call` node            | RFC-011  | M    |
| MCP allow-list（SSRF defense）       | RFC-011  | S    |
| Memory 向量檢索（embedding-based）   | RFC-011  | L    |
| Media providers 接入 workflow（_exec_image 改走 registry）| RFC-011 | M |

## Pillar 2：multi-replica 安全

| Item                          | 影響                          | 預估 |
| ----------------------------- | ----------------------------- | ---- |
| trigger advisory lock         | 多副本不重複觸發                | S    |
| usage log 寫入冪等            | 重試不重複計帳                  | S    |
| Helm 補齊其餘 service template | gateway/knowledge/auth/chat/ui | M    |

## Pillar 3：工程基礎強化

| Item                          | 預估 |
| ----------------------------- | ---- |
| eslint + vue-eslint-parser    | S    |
| vitest 50% 覆蓋率（前端）      | L    |
| 各服務補 pytest（knowledge/auth/chat）| M |
| OTel auto-instrument 各服務     | M    |
| Docs site CI auto-deploy      | S    |

## Pillar 4：UX 收尾

| Item                            | 預估 |
| ------------------------------- | ---- |
| dark mode 全量視圖（Tier 1~3）    | M    |
| toast/dialog 替換完所有 alert    | S    |
| onboarding tour（新使用者首次）   | M    |
| 空狀態插畫（4 主要頁面）         | M    |

## Pillar 5：商業功能

| Item                            | 預估 |
| ------------------------------- | ---- |
| Quota 80% / 100% email 告警      | S    |
| API key 自動 rotate（90 天提示）  | M    |
| 部門級用量 dashboard（per-app）   | M    |
| Audit log export                | S    |

## Pillar 6（後續，不在 v2.1 內）

- **v3.0 Nuxt 3 migration**（RFC-004）— 大型；獨立 milestone
- **多媒體節點 GA**（影片生成、Realtime API）— M4 收尾後評估
- **Sandbox M4-A nsjail**：M4 收尾再評估
- **SSO Identity Provider 整合**（SAML / OIDC enterprise）

## 時程草案

| 週   | 內容                                |
| ---- | ----------------------------------- |
| 1~2  | Pillar 1（dispatcher / memory_save / mcp_call） |
| 3    | Pillar 2（advisory lock + Helm 補齊）|
| 4~5  | Pillar 1（vector recall）+ Pillar 4 onboarding |
| 6    | Pillar 3 + Pillar 5                |
| 7    | UAT + 修補                          |
| 8    | v2.1 release                       |
