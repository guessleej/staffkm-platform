"""RAG eval harness — v3.3 C5.

usage:
    python tools/eval/rag_eval.py \\
        --base http://localhost \\
        --token <JWT> \\
        --kb-id <UUID> \\
        --dataset tools/eval/rag_eval_dataset.json \\
        --modes vector hybrid fts \\
        --rerank none cohere ollama \\
        --output docs/perf/v3.3-rag-bench-results.md

依賴：httpx（後端 service 已用），無需額外裝。
metric：hit@5 / MRR（基於 expected_paragraph_ids）。
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
from pathlib import Path

import httpx


# ── reranker preset 表 ────────────────────────────────────────────────────────
RERANK_PRESETS: dict[str, dict | None] = {
    "none": None,
    "cohere": {
        "type": "cohere",
        "api_key": os.environ.get("COHERE_API_KEY", ""),
        "model_name": "rerank-multilingual-v3.0",
    },
    "ollama": {
        "type": "ollama",
        "base_url": os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        "model_name": os.environ.get("OLLAMA_RERANK_MODEL", "bge-reranker-v2-m3"),
        "embed_model": os.environ.get("OLLAMA_EMBED_MODEL", "bge-m3"),
    },
    "http": {
        "type": "http",
        "base_url": os.environ.get("RERANKER_BASE_URL", "http://localhost:8080"),
        "model_name": os.environ.get("RERANKER_MODEL", "bge-reranker-v2-m3"),
        "api_key": os.environ.get("RERANKER_API_KEY", ""),
    },
}


async def run_mode(
    client: httpx.AsyncClient,
    base: str,
    token: str,
    kb_id: str,
    dataset: dict,
    mode: str,
    rerank_config: dict | None,
) -> dict[str, float]:
    hits_at_5: list[float] = []
    mrr_scores: list[float] = []
    skipped = 0
    for q in dataset["queries"]:
        expected = set(q.get("expected_paragraph_ids") or [])
        if not expected:
            skipped += 1
            continue

        body: dict = {
            "query": q["query"],
            "kb_id": kb_id,
            "top_k": 10,
            "search_mode": mode,
            "vector_weight": 0.7,
        }
        if rerank_config:
            body["reranker"] = rerank_config
            body["rerank_top_n"] = 5

        r = await client.post(
            f"{base}/api/v1/knowledge/hit-test",
            headers={"Authorization": f"Bearer {token}"},
            json=body,
        )
        r.raise_for_status()
        results = r.json()["data"]["results"]
        top5_ids = [str(x["paragraph_id"]) for x in results[:5]]

        # hit@5
        hits_at_5.append(1.0 if any(pid in expected for pid in top5_ids) else 0.0)
        # MRR
        rank = next(
            (i + 1 for i, pid in enumerate(top5_ids) if pid in expected),
            0,
        )
        mrr_scores.append(1.0 / rank if rank else 0.0)

    if not hits_at_5:
        return {"hit@5": float("nan"), "MRR": float("nan"), "n": 0, "skipped": skipped}
    return {
        "hit@5": sum(hits_at_5) / len(hits_at_5),
        "MRR": statistics.mean(mrr_scores),
        "n": float(len(hits_at_5)),
        "skipped": float(skipped),
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True, help="gateway base URL, e.g. http://localhost")
    parser.add_argument("--token", required=True, help="JWT access token")
    parser.add_argument("--kb-id", required=True, help="目標 KB UUID")
    parser.add_argument("--dataset", required=True)
    parser.add_argument(
        "--modes", nargs="+", default=["vector", "hybrid", "fts"],
        choices=["vector", "hybrid", "fts"],
    )
    parser.add_argument(
        "--rerank", nargs="+", default=["none"],
        choices=list(RERANK_PRESETS.keys()),
    )
    parser.add_argument("--output", default="docs/perf/v3.3-rag-bench-results.md")
    args = parser.parse_args()

    dataset = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
    results: dict[str, dict[str, float]] = {}

    async with httpx.AsyncClient(timeout=60.0) as client:
        for mode in args.modes:
            for rerank_name in args.rerank:
                rcfg = RERANK_PRESETS[rerank_name]
                key = f"{mode}+{rerank_name}"
                print(f"[run] {key} ...")
                try:
                    results[key] = await run_mode(
                        client, args.base, args.token, args.kb_id,
                        dataset, mode, rcfg,
                    )
                except Exception as e:
                    print(f"[fail] {key}: {e}")
                    results[key] = {
                        "hit@5": float("nan"), "MRR": float("nan"),
                        "n": 0, "skipped": 0,
                    }

    # ── 輸出 markdown ────────────────────────────────────────────────────────
    lines = [
        "# RAG eval results — v3.3",
        "",
        f"- dataset: `{args.dataset}`",
        f"- kb_id: `{args.kb_id}`",
        f"- queries: {len(dataset['queries'])}",
        "",
        "| mode+rerank | n | hit@5 | MRR | skipped |",
        "|-------------|----|-------|------|---------|",
    ]
    for k, v in results.items():
        lines.append(
            f"| {k} | {int(v['n'])} | {v['hit@5']:.3f} | {v['MRR']:.3f} | {int(v['skipped'])} |"
        )
    out = "\n".join(lines) + "\n"
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(out, encoding="utf-8")
    print(out)


if __name__ == "__main__":
    asyncio.run(main())
