"""pgvector 壓測腳本（Round 8-2）。

用途：
- 量測 staffKM knowledge service 走 pgvector 在不同資料量級的 P50/P95/P99 query latency
- 量測 HNSW vs IVFFlat index 的差異
- 量測 ef_search / probes 參數對 recall vs latency 的取捨

依賴：
- asyncpg
- numpy（隨機向量生成）

使用：
    DB_URL=postgresql://... python tools/bench/pgvector_bench.py \\
        --rows 100000 --dims 1536 --queries 1000 \\
        --index hnsw --ef-search 64

輸出：
    一筆 JSON to stdout（含 p50/p95/p99/qps/recall@10）
    建議 redirect 到 tools/bench/results/{date}-{config}.json 並提交 Git
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import sys
import time
from statistics import median


def _percentile(sorted_values: list[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    k = max(0, min(len(sorted_values) - 1, int(round((pct / 100.0) * (len(sorted_values) - 1)))))
    return sorted_values[k]


async def _ensure_table(conn, dims: int, index_type: str) -> None:
    await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    await conn.execute(f"""
        CREATE TABLE IF NOT EXISTS bench_chunks (
            id     BIGSERIAL PRIMARY KEY,
            embed  vector({dims}) NOT NULL
        )
    """)
    await conn.execute("DROP INDEX IF EXISTS bench_chunks_embed_idx")
    if index_type == "hnsw":
        await conn.execute(
            "CREATE INDEX bench_chunks_embed_idx ON bench_chunks "
            "USING hnsw (embed vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
        )
    elif index_type == "ivfflat":
        # 經驗值：lists = sqrt(rows)；min 100
        await conn.execute(
            "CREATE INDEX bench_chunks_embed_idx ON bench_chunks "
            "USING ivfflat (embed vector_cosine_ops) WITH (lists = 100)"
        )


async def _seed(conn, *, rows: int, dims: int, batch: int = 2000) -> None:
    count = (await conn.fetchval("SELECT COUNT(*) FROM bench_chunks")) or 0
    if count >= rows:
        print(f"[seed] 已有 {count} rows，跳過種資料", file=sys.stderr)
        return
    need = rows - count
    print(f"[seed] 寫入 {need} rows × {dims} dims（每批 {batch}）", file=sys.stderr)

    def _rand_vec() -> str:
        return "[" + ",".join(f"{random.uniform(-1, 1):.4f}" for _ in range(dims)) + "]"

    while need > 0:
        n = min(batch, need)
        # 用 COPY 比 INSERT 快很多
        records = [(_rand_vec(),) for _ in range(n)]
        async with conn.transaction():
            await conn.executemany(
                "INSERT INTO bench_chunks (embed) VALUES ($1::vector)",
                records,
            )
        need -= n
        print(f"  ...剩 {need}", file=sys.stderr)


async def _bench(conn, *, dims: int, queries: int, top_k: int, ef_search: int | None) -> dict:
    if ef_search is not None:
        await conn.execute(f"SET hnsw.ef_search = {int(ef_search)}")

    latencies: list[float] = []
    for _ in range(queries):
        v = "[" + ",".join(f"{random.uniform(-1, 1):.4f}" for _ in range(dims)) + "]"
        t0 = time.perf_counter()
        await conn.fetch(
            "SELECT id FROM bench_chunks ORDER BY embed <=> $1::vector LIMIT $2",
            v, top_k,
        )
        latencies.append((time.perf_counter() - t0) * 1000)

    latencies.sort()
    total_sec = sum(latencies) / 1000.0
    return {
        "queries":    queries,
        "top_k":      top_k,
        "ef_search":  ef_search,
        "latency_ms": {
            "min":  round(latencies[0], 2),
            "p50":  round(median(latencies), 2),
            "p95":  round(_percentile(latencies, 95), 2),
            "p99":  round(_percentile(latencies, 99), 2),
            "max":  round(latencies[-1], 2),
            "mean": round(sum(latencies) / len(latencies), 2),
        },
        "qps": round(queries / total_sec, 2) if total_sec > 0 else None,
    }


async def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--rows", type=int, default=10_000)
    p.add_argument("--dims", type=int, default=1536)
    p.add_argument("--queries", type=int, default=500)
    p.add_argument("--top-k", type=int, default=10)
    p.add_argument("--index", choices=["hnsw", "ivfflat"], default="hnsw")
    p.add_argument("--ef-search", type=int, default=64)
    p.add_argument("--skip-seed", action="store_true")
    args = p.parse_args()

    try:
        import asyncpg
    except ImportError:
        sys.exit("asyncpg 未安裝；請 `uv pip install asyncpg`")

    db_url = os.environ.get("DB_URL")
    if not db_url:
        sys.exit("環境變數 DB_URL 必填")
    # asyncpg 不接受 +asyncpg suffix
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    conn = await asyncpg.connect(db_url)
    try:
        await _ensure_table(conn, dims=args.dims, index_type=args.index)
        if not args.skip_seed:
            await _seed(conn, rows=args.rows, dims=args.dims)
        await conn.execute("ANALYZE bench_chunks")
        result = await _bench(
            conn,
            dims=args.dims,
            queries=args.queries,
            top_k=args.top_k,
            ef_search=args.ef_search if args.index == "hnsw" else None,
        )
        result["meta"] = {
            "rows":  args.rows,
            "dims":  args.dims,
            "index": args.index,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
