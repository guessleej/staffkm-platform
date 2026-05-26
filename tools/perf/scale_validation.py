#!/usr/bin/env python3
"""規模驗證 harness — 真 pgvector，量測「10 萬段落 + 多 KB + 並發查詢」的實際數字。

目的：把 RAG 召回從「小語料單一 KB」推到接近 production 的量級，拿**真實測得**的
index build / 查詢延遲（p50/p95/p99）/ 並發吞吐 / KB 隔離 / ivfflat.probes 效果，
不是「設計上應該可以」。

獨立工具（只依賴 asyncpg + numpy），不 import 任何 service。查詢 SQL 鏡像
`services/knowledge/app/core/vectorstore.hybrid_search` 的 vector 模式（含 SET LOCAL
ivfflat.probes），以反映真實查詢路徑與真實 ivfflat 索引行為。

用法：
    pip install asyncpg numpy
    docker run -d --name pg -e POSTGRES_USER=staffkm -e POSTGRES_PASSWORD=staffkm_secret \\
        -e POSTGRES_DB=staffkm_scale -p 55433:5432 --shm-size=512m pgvector/pgvector:pg16
    SCALE_DB_URL=postgresql://staffkm:staffkm_secret@localhost:55433/staffkm_scale \\
        python tools/perf/scale_validation.py --paragraphs 100000 --kbs 10 --dim 1024 \\
        --queries 300 --concurrency 32 --json out.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import time
import uuid

import asyncpg
import numpy as np


def _pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = max(0, min(len(s) - 1, int(round((p / 100.0) * (len(s) - 1)))))
    return s[k]


def _vec_literal(arr: np.ndarray) -> str:
    return "[" + ",".join("%.4f" % x for x in arr) + "]"


async def _setup_schema(conn, dim: int) -> None:
    await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    await conn.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    await conn.execute("DROP TABLE IF EXISTS paragraph_embeddings, paragraphs, documents CASCADE")
    await conn.execute("""
        CREATE TABLE documents (id uuid PRIMARY KEY, name text)
    """)
    await conn.execute("""
        CREATE TABLE paragraphs (
            id uuid PRIMARY KEY, document_id uuid, knowledge_base_id uuid,
            content text, title text, meta jsonb, order_index integer DEFAULT 0,
            is_active boolean NOT NULL DEFAULT true, search_vector tsvector
        )
    """)
    await conn.execute(f"""
        CREATE TABLE paragraph_embeddings (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            paragraph_id uuid NOT NULL REFERENCES paragraphs(id) ON DELETE CASCADE,
            kb_id uuid NOT NULL, embedding vector({dim}),
            CONSTRAINT uniq_para_embed UNIQUE (paragraph_id)
        )
    """)


async def _load(conn, *, n_para: int, n_kbs: int, dim: int, batch: int) -> dict:
    kb_ids = [uuid.uuid4() for _ in range(n_kbs)]
    doc_ids = [uuid.uuid4() for _ in range(n_kbs)]

    t0 = time.monotonic()
    await conn.executemany(
        "INSERT INTO documents (id, name) VALUES ($1, $2)",
        [(d, f"doc-{i}") for i, d in enumerate(doc_ids)],
    )

    rng = np.random.default_rng(42)
    loaded = 0
    while loaded < n_para:
        n = min(batch, n_para - loaded)
        kb_idx = rng.integers(0, n_kbs, size=n)
        pids = [uuid.uuid4() for _ in range(n)]
        # paragraphs（COPY text）
        para_rows = (
            f"{pids[j]}\t{doc_ids[kb_idx[j]]}\t{kb_ids[kb_idx[j]]}\tpara {loaded + j}\tt"
            for j in range(n)
        )
        await conn.copy_to_table(
            "paragraphs",
            source=_byte_iter(para_rows),
            columns=["id", "document_id", "knowledge_base_id", "content", "is_active"],
            format="text",
        )
        # embeddings（COPY text；向量字面值）
        vecs = rng.random((n, dim), dtype=np.float64)
        emb_rows = (
            f"{pids[j]}\t{kb_ids[kb_idx[j]]}\t{_vec_literal(vecs[j])}"
            for j in range(n)
        )
        await conn.copy_to_table(
            "paragraph_embeddings",
            source=_byte_iter(emb_rows),
            columns=["paragraph_id", "kb_id", "embedding"],
            format="text",
        )
        loaded += n
        print(f"  loaded {loaded}/{n_para}", end="\r", flush=True)
    print()
    load_s = time.monotonic() - t0

    # ivfflat index 建在「載入後」（best practice：先灌資料再建索引）
    # ivfflat 建索引吃 maintenance_work_mem（100k×1024 約需 ~86MB）→ 拉高避免 ProgramLimitExceeded。
    # production 同理：大庫重建索引前要確保 maintenance_work_mem 足夠（見 docs/perf）。
    await conn.execute("SET maintenance_work_mem = '256MB'")
    lists = max(10, int(np.sqrt(n_para)))
    t1 = time.monotonic()
    await conn.execute(
        f"CREATE INDEX idx_pe_vec ON paragraph_embeddings "
        f"USING ivfflat (embedding vector_cosine_ops) WITH (lists = {lists})"
    )
    await conn.execute("CREATE INDEX idx_pe_kb ON paragraph_embeddings(kb_id)")
    await conn.execute("ANALYZE paragraph_embeddings")
    index_s = time.monotonic() - t1

    return {"kb_ids": kb_ids, "load_s": load_s, "index_s": index_s, "lists": lists}


async def _byte_iter(rows):
    for r in rows:
        yield (r + "\n").encode()


# vectorstore.hybrid_search 的 vector 模式 SQL（鏡像；JOIN paragraphs+documents、閾值、ORDER BY <=>）
_VEC_SQL = """
SELECT p.id, (1 - (pe.embedding <=> $1::vector)) AS score
FROM paragraph_embeddings pe
JOIN paragraphs p ON p.id = pe.paragraph_id
JOIN documents  d ON d.id = p.document_id
WHERE pe.kb_id = $2 AND p.is_active = true
  AND (1 - (pe.embedding <=> $1::vector)) >= $3
ORDER BY pe.embedding <=> $1::vector
LIMIT $4
"""


async def _one_query(conn, kb_id, qvec: str, probes: int, top_k: int, threshold: float):
    async with conn.transaction():
        await conn.execute(f"SET LOCAL ivfflat.probes = {int(probes)}")
        t = time.monotonic()
        rows = await conn.fetch(_VEC_SQL, qvec, kb_id, threshold, top_k)
        return (time.monotonic() - t) * 1000.0, rows


async def _bench_serial(pool, kb_ids, *, dim, probes, n_queries, top_k, threshold) -> list[float]:
    rng = np.random.default_rng(7)
    lat = []
    async with pool.acquire() as conn:
        for i in range(n_queries):
            qvec = _vec_literal(rng.random(dim))
            kb = kb_ids[i % len(kb_ids)]
            ms, _ = await _one_query(conn, kb, qvec, probes, top_k, threshold)
            lat.append(ms)
    return lat


async def _bench_concurrent(pool, kb_ids, *, dim, probes, n_queries, concurrency, top_k, threshold):
    rng = np.random.default_rng(11)
    queries = [(_vec_literal(rng.random(dim)), kb_ids[i % len(kb_ids)]) for i in range(n_queries)]
    sem = asyncio.Semaphore(concurrency)
    lat: list[float] = []

    async def worker(qvec, kb):
        async with sem, pool.acquire() as conn:
            ms, _ = await _one_query(conn, kb, qvec, probes, top_k, threshold)
            lat.append(ms)

    t0 = time.monotonic()
    await asyncio.gather(*(worker(q, kb) for q, kb in queries))
    wall = time.monotonic() - t0
    return lat, wall


async def _verify_kb_isolation(pool, kb_ids, dim, top_k) -> bool:
    rng = np.random.default_rng(3)
    async with pool.acquire() as conn:
        for kb in kb_ids[:3]:
            qvec = _vec_literal(rng.random(dim))
            async with conn.transaction():
                await conn.execute("SET LOCAL ivfflat.probes = 10")
                rows = await conn.fetch(
                    "SELECT pe.kb_id FROM paragraph_embeddings pe "
                    "JOIN paragraphs p ON p.id = pe.paragraph_id "
                    "WHERE pe.kb_id = $1 ORDER BY pe.embedding <=> $2::vector LIMIT $3",
                    kb, qvec, top_k,
                )
            if any(r["kb_id"] != kb for r in rows):
                return False
    return True


def _summary(lat: list[float]) -> dict:
    return {
        "n": len(lat),
        "mean_ms": round(statistics.mean(lat), 2),
        "p50_ms": round(_pct(lat, 50), 2),
        "p95_ms": round(_pct(lat, 95), 2),
        "p99_ms": round(_pct(lat, 99), 2),
        "max_ms": round(max(lat), 2),
    }


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paragraphs", type=int, default=100_000)
    ap.add_argument("--kbs", type=int, default=10)
    ap.add_argument("--dim", type=int, default=1024)
    ap.add_argument("--queries", type=int, default=300)
    ap.add_argument("--concurrency", type=int, default=32)
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--threshold", type=float, default=0.0)
    ap.add_argument("--batch", type=int, default=10_000)
    ap.add_argument("--json", type=str, default="")
    args = ap.parse_args()

    db_url = os.environ.get("SCALE_DB_URL")
    if not db_url:
        raise SystemExit("set SCALE_DB_URL (postgresql://...)")

    report: dict = {"config": vars(args)}
    conn = await asyncpg.connect(db_url)
    try:
        print(f"[1/5] schema (dim={args.dim})")
        await _setup_schema(conn, args.dim)
        print(f"[2/5] load {args.paragraphs} paras across {args.kbs} KBs")
        loaded = await _load(conn, n_para=args.paragraphs, n_kbs=args.kbs,
                             dim=args.dim, batch=args.batch)
    finally:
        await conn.close()

    report["load"] = {
        "paragraphs": args.paragraphs, "kbs": args.kbs, "dim": args.dim,
        "load_seconds": round(loaded["load_s"], 1),
        "index_build_seconds": round(loaded["index_s"], 1),
        "ivfflat_lists": loaded["lists"],
    }
    print(f"      load={loaded['load_s']:.1f}s  index_build={loaded['index_s']:.1f}s  lists={loaded['lists']}")

    pool = await asyncpg.create_pool(db_url, min_size=args.concurrency, max_size=args.concurrency + 4)
    try:
        print("[3/5] serial latency: probes=1 vs probes=10")
        lat_p1 = await _bench_serial(pool, loaded["kb_ids"], dim=args.dim, probes=1,
                                     n_queries=args.queries, top_k=args.top_k, threshold=args.threshold)
        lat_p10 = await _bench_serial(pool, loaded["kb_ids"], dim=args.dim, probes=10,
                                      n_queries=args.queries, top_k=args.top_k, threshold=args.threshold)
        report["serial_probes_1"] = _summary(lat_p1)
        report["serial_probes_10"] = _summary(lat_p10)

        print(f"[4/5] concurrent: {args.concurrency} workers × {args.queries} queries (probes=10)")
        lat_c, wall = await _bench_concurrent(pool, loaded["kb_ids"], dim=args.dim, probes=10,
                                              n_queries=args.queries, concurrency=args.concurrency,
                                              top_k=args.top_k, threshold=args.threshold)
        report["concurrent"] = {
            **_summary(lat_c),
            "concurrency": args.concurrency,
            "wall_seconds": round(wall, 2),
            "throughput_qps": round(args.queries / wall, 1),
        }

        print("[5/5] KB isolation")
        report["kb_isolation_ok"] = await _verify_kb_isolation(pool, loaded["kb_ids"], args.dim, args.top_k)
    finally:
        await pool.close()

    print("\n===== SCALE VALIDATION REPORT =====")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.json:
        with open(args.json, "w") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    asyncio.run(main())
