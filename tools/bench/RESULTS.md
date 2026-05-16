# pgvector 壓測歷史結果

> 每次新測請在表格末尾新增一行；對應 JSON 存於 `tools/bench/results/`。

| Date       | rows  | dims | index | ef_search | p50  | p95   | p99   | QPS  | 備註                       |
| ---------- | ----- | ---- | ----- | --------- | ---- | ----- | ----- | ---- | -------------------------- |
| _pending_  | _to be filled by first run_                                                                                  |

## 歷史結論（持續更新）

- **線上知識庫可用基準**：P95 < 50ms（依使用者察覺值反推）
- **可接受區間**：P99 < 100ms（偶發查詢可容忍）
- **退化警戒**：P95 > 100ms 任一檔位即觸發 root cause 調查

## 待補測項

- [ ] recall@10 對照 brute force
- [ ] concurrent query（10 / 50 / 100 並發）
- [ ] embedding 維度比較（768 / 1024 / 1536 / 3072）
- [ ] HNSW m / ef_construction 參數掃描
