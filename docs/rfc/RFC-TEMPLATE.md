# RFC-NNN: <簡短標題>

| 欄位 | 內容 |
|------|------|
| 編號 | RFC-NNN |
| 提案者 | @your-name |
| 狀態 | Draft / Review / Accepted / Rejected / Superseded |
| 建立日期 | YYYY-MM-DD |
| 最後更新 | YYYY-MM-DD |
| Reviewers | @arch @lead-be @lead-fe |
| 取代 / 被取代 | 無 / RFC-XXX |

---

## 1. 摘要（Summary）

一段話講清楚這個提案要做什麼、為什麼。reviewer 看完這段就要知道是否需要繼續讀。

## 2. 動機（Motivation）

- 現況有什麼問題？
- 為什麼現在要做？不做會怎樣？
- 用實際的使用情境或量化數據說明（latency 高、用戶抱怨、技術債利息）。

## 3. 目標與非目標（Goals / Non-Goals）

**目標**
- [ ] G1：…
- [ ] G2：…

**非目標**（明確排除，避免 scope creep）
- N1：…

## 4. 提案設計（Proposed Design）

### 4.1 架構圖

```
（用 ASCII 或 Mermaid 畫出系統圖）
```

### 4.2 核心介面 / Schema

```python
# Python signature / SQL DDL / TypeScript type
```

### 4.3 流程

1. step
2. step
3. step

### 4.4 失敗處理

- 哪些操作可能失敗？怎麼 retry / fallback？

## 5. 替代方案（Alternatives Considered）

| 方案 | 優點 | 缺點 | 為何不選 |
|------|------|------|----------|
| A | … | … | … |
| B | … | … | … |

## 6. 風險與緩解（Risks）

| 風險 | 機率 | 衝擊 | 緩解 |
|------|------|------|------|
| … | 高/中/低 | 高/中/低 | … |

## 7. 影響範圍（Impact）

- **資料庫**：是否需要 migration？資料是否需要回填？
- **API**：是否 breaking change？是否需要版本化？
- **效能**：預期 QPS / latency 變化
- **資安**：是否引入新的 attack surface？
- **依賴**：新增 / 移除哪些套件或服務？

## 8. 推出計畫（Rollout Plan）

- [ ] Stage 1：feature flag 在 dev 開啟
- [ ] Stage 2：staging 全開、跑 E2E
- [ ] Stage 3：production 5% canary
- [ ] Stage 4：production 100%
- [ ] Stage 5：移除 feature flag、刪除舊程式

回滾策略：…

## 9. 量測指標（Success Metrics）

- 上線後 30 天看：…
- 達標條件：…
- 不達標處置：…

## 10. 開放問題（Open Questions）

- [ ] Q1：…（@person to resolve by date）

## 11. 參考資料（References）

- [連結 1](https://…)
- [相關 RFC：RFC-XXX]
