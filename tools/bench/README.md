# Bench 工具集

## pgvector 壓測

### 跑一次基準

```bash
# 預設：10k rows / 1536 dims / HNSW / ef_search=64 / 500 queries
DB_URL="postgresql://postgres:postgres@localhost:5432/staffkm" \
  python tools/bench/pgvector_bench.py

# 大量級
DB_URL="..." python tools/bench/pgvector_bench.py \
  --rows 1000000 --dims 768 --queries 1000 --ef-search 100

# 換 IVFFlat 對照
DB_URL="..." python tools/bench/pgvector_bench.py \
  --index ivfflat --rows 100000
```

### 報告模板

每次跑完請存到 `tools/bench/results/{YYYY-MM-DD}-{label}.json`，並在 `RESULTS.md` 加一行：

```markdown
| Date       | rows  | dims | index | ef  | p50  | p95   | p99   | QPS  | 備註         |
| ---------- | ----- | ---- | ----- | --- | ---- | ----- | ----- | ---- | ------------ |
| 2026-05-16 | 100k  | 1536 | hnsw  | 64  | 4.2  | 12.8  | 25.1  | 480  | M2 baseline  |
| 2026-05-16 | 1M    | 1536 | hnsw  | 64  | 11.7 | 38.2  | 72.4  | 195  |              |
| 2026-05-16 | 1M    | 768  | hnsw  | 64  | 7.4  | 22.1  | 41.6  | 290  | 半維提速 ×1.5 |
```

### 解讀建議

- **P95 < 50ms** 為線上知識庫可用基準；超過要調 `ef_search` 或 reduce dims
- **HNSW vs IVFFlat**：寫多 / 動態更新 → HNSW；唯讀 / 大規模 → IVFFlat 配高 lists
- **dims 對 latency 影響大**：1536 → 768 通常能省 ~40% 時間；換 embedding model 前先量

## 後續

- 加入 recall@10 量測（需 ground truth；可隨機抽樣對比 brute force）
- 多並發測試（asyncio.gather N concurrent queries）
- CI 上跑 nightly 並出趨勢圖（M5）
