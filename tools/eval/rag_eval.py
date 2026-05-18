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


def resolve_anchors(dataset: dict, seeded: dict | None) -> int:
    """把 dataset 內每條 query 的 expected_corpus_anchors 解析為 paragraph_id。

    回傳新增解析的 id 總數。若 seeded 為 None / 對不到 file，保留原 expected_paragraph_ids。
    比對規則：anchor.file 對應 seeded.documents[].file；title_contains 子字串 match
    paragraph.title（fallback：match content 前綴）。每個 anchor 取首個 match。
    """
    if not seeded:
        return 0
    file_index = {d["file"]: d for d in seeded.get("documents", [])}
    added = 0
    for q in dataset["queries"]:
        anchors = q.get("expected_corpus_anchors") or []
        existing = set(q.get("expected_paragraph_ids") or [])
        for a in anchors:
            doc = file_index.get(a.get("file"))
            if not doc:
                print(f"[anchor-miss] q={q['id']} file={a.get('file')} not in seeded")
                continue
            needle = a.get("title_contains", "")
            matched = None
            for p in doc["paragraphs"]:
                hay = (p.get("title") or "") + " " + (p.get("content") or "")
                if needle and needle in hay:
                    matched = p["id"]
                    break
            if matched and matched not in existing:
                existing.add(matched)
                added += 1
            elif not matched:
                print(
                    f"[anchor-miss] q={q['id']} file={a.get('file')} "
                    f"title_contains={needle!r} no paragraph match"
                )
        q["expected_paragraph_ids"] = list(existing)
    return added


# ── v3.7 P3: LLM-as-judge ───────────────────────────────────────────────────

JUDGE_PROMPT = """你是一位 RAG 系統評分員。給定一個 query 與檢索出來的段落（top-k），請評估 \
這些段落是否足以回答 query。

評分標準（0-5）：
0 = 完全無關
1 = 微弱相關
2 = 部分相關但缺關鍵資訊
3 = 大致相關，可作參考
4 = 高度相關，幾乎可回答
5 = 完整命中，可直接回答

{rubric_extra}

Query：{query}

檢索段落（top-{k}）：
{passages}

只輸出一個整數分數（0-5），不要其他文字。"""


async def llm_judge(
    client: httpx.AsyncClient,
    *,
    base_url: str,
    api_key: str,
    judge_model: str,
    query: str,
    passages: list[str],
    rubric_extra: str = "",
) -> float | None:
    """呼叫 judge model 評分，回 0-5 float。失敗回 None。

    OpenAI-compatible endpoint（base_url 範例：https://api.openai.com/v1
    或 http://embedder:11434/v1 for Ollama）。
    """
    prompt = JUDGE_PROMPT.format(
        query=query,
        k=len(passages),
        passages="\n---\n".join(f"[{i+1}] {p[:300]}" for i, p in enumerate(passages)),
        rubric_extra=rubric_extra or "",
    )
    try:
        r = await client.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
            json={
                "model": judge_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
                "max_tokens": 8,
            },
            timeout=30.0,
        )
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"].strip()
        # 取第一個數字
        import re
        m = re.search(r"\d+", content)
        if not m:
            return None
        score = float(m.group())
        return max(0.0, min(5.0, score))
    except Exception as e:
        print(f"[judge-error] {e}")
        return None


async def run_mode(
    client: httpx.AsyncClient,
    base: str,
    token: str,
    kb_id: str,
    dataset: dict,
    mode: str,
    rerank_config: dict | None,
    judge_cfgs: list[dict] | None = None,  # v3.8 P3: multi-judge
) -> dict[str, float]:
    hits_at_5: list[float] = []
    mrr_scores: list[float] = []
    # v3.8 P3: per-judge 累計，最後算 consensus
    judge_scores_by_model: dict[str, list[float]] = {}
    if judge_cfgs:
        for jc in judge_cfgs:
            judge_scores_by_model[jc["model"]] = []
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

        # v3.7 P3 + v3.8 P3: LLM-as-judge — 每個 judge 都評一次
        if judge_cfgs:
            passages = [r.get("content", "") for r in results[:5]]
            rubric_extra = q.get("judge_criteria", "")
            for jc in judge_cfgs:
                score = await llm_judge(
                    client,
                    base_url=jc["base_url"],
                    api_key=jc["api_key"],
                    judge_model=jc["model"],
                    query=q["query"],
                    passages=passages,
                    rubric_extra=rubric_extra,
                )
                if score is not None:
                    judge_scores_by_model[jc["model"]].append(score)

    if not hits_at_5:
        return {"hit@5": float("nan"), "MRR": float("nan"),
                "n": 0, "skipped": skipped}
    out: dict[str, float | dict] = {
        "hit@5": sum(hits_at_5) / len(hits_at_5),
        "MRR": statistics.mean(mrr_scores),
        "n": float(len(hits_at_5)),
        "skipped": float(skipped),
    }
    if judge_cfgs:
        # 個別 judge 平均
        per_judge = {}
        all_means: list[float] = []
        for model, scores in judge_scores_by_model.items():
            avg = statistics.mean(scores) if scores else float("nan")
            per_judge[model] = {"avg": avg, "n": len(scores)}
            if scores:
                all_means.append(avg)
        out["judge_per_model"] = per_judge
        # consensus = mean of means; stdev 給 judge 間分歧度
        if all_means:
            out["judge_consensus"] = statistics.mean(all_means)
            out["judge_stdev"] = statistics.stdev(all_means) if len(all_means) > 1 else 0.0
        else:
            out["judge_consensus"] = float("nan")
            out["judge_stdev"] = float("nan")
    return out


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
    # v3.7 P3 / v3.8 P3: LLM-as-judge (multi-judge averaging)
    parser.add_argument(
        "--judge-model", default=None,
        help="單一 judge model（v3.7 相容；新版建議用 --judge-models）",
    )
    parser.add_argument(
        "--judge-models", nargs="+", default=None,
        help="v3.8 P3: 多個 judge models 取平均（每 query 對每個 judge 評一次）。"
             "預設用 --judge-base + --judge-key；想對不同 judge 用不同 base/key 可用 "
             "format 'model@base@key' (例: gpt-4o-mini@https://api.openai.com/v1@sk-xxx)",
    )
    parser.add_argument(
        "--judge-base", default=os.environ.get("JUDGE_BASE_URL", "https://api.openai.com/v1"),
        help="judge model 的 OpenAI-compat endpoint (預設給所有 judge 用)",
    )
    parser.add_argument(
        "--judge-key", default=os.environ.get("JUDGE_API_KEY", os.environ.get("OPENAI_API_KEY", "")),
        help="judge model API key (預設給所有 judge 用)",
    )
    parser.add_argument(
        "--seeded",
        default=None,
        help="seeded_paragraphs.json（由 seed_eval_kb.py 輸出），用來把 dataset "
             "中 expected_corpus_anchors 解析為實際 paragraph_id",
    )
    args = parser.parse_args()

    dataset = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
    seeded = None
    if args.seeded:
        seeded = json.loads(Path(args.seeded).read_text(encoding="utf-8"))
        added = resolve_anchors(dataset, seeded)
        print(f"[anchors] resolved {added} paragraph_id(s) from seeded corpus")
    results: dict[str, dict[str, float]] = {}

    # v3.8 P3: build judge_cfgs (list)
    judge_cfgs: list[dict] | None = None
    raw_models = args.judge_models or ([args.judge_model] if args.judge_model else None)
    if raw_models:
        judge_cfgs = []
        for spec in raw_models:
            # parse `model@base@key` format
            parts = spec.split("@")
            jc = {
                "model":    parts[0],
                "base_url": parts[1] if len(parts) > 1 and parts[1] else args.judge_base,
                "api_key":  parts[2] if len(parts) > 2 and parts[2] else args.judge_key,
            }
            judge_cfgs.append(jc)
            print(f"[judge] enabled: {jc['model']} via {jc['base_url']}")

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
                        judge_cfgs=judge_cfgs,
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
        ("| mode+rerank | n | hit@5 | MRR | judge_consensus | judge_stdev | skipped |"
         if judge_cfgs else
         "| mode+rerank | n | hit@5 | MRR | skipped |"),
        ("|-------------|----|-------|------|-----------------|-------------|---------|"
         if judge_cfgs else
         "|-------------|----|-------|------|---------|"),
    ]
    for k, v in results.items():
        if judge_cfgs:
            jc = v.get("judge_consensus", float("nan"))
            jc_str = f"{jc:.2f}" if jc == jc else "nan"  # NaN check
            js = v.get("judge_stdev", float("nan"))
            js_str = f"{js:.2f}" if js == js else "nan"
            lines.append(
                f"| {k} | {int(v['n'])} | {v['hit@5']:.3f} | {v['MRR']:.3f} | {jc_str} | {js_str} | {int(v['skipped'])} |"
            )
        else:
            lines.append(
                f"| {k} | {int(v['n'])} | {v['hit@5']:.3f} | {v['MRR']:.3f} | {int(v['skipped'])} |"
            )

    # v3.8 P3: per-judge breakdown
    if judge_cfgs:
        lines.append("")
        lines.append("## Per-judge breakdown")
        lines.append("")
        lines.append("| mode+rerank | " + " | ".join(jc["model"] for jc in judge_cfgs) + " |")
        lines.append("|" + "---|" * (len(judge_cfgs) + 1))
        for k, v in results.items():
            pj = v.get("judge_per_model", {})
            cells = []
            for jc in judge_cfgs:
                d = pj.get(jc["model"], {})
                avg = d.get("avg", float("nan"))
                n = d.get("n", 0)
                avg_str = f"{avg:.2f} (n={n})" if avg == avg else "nan"
                cells.append(avg_str)
            lines.append(f"| {k} | " + " | ".join(cells) + " |")
    out = "\n".join(lines) + "\n"
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(out, encoding="utf-8")
    print(out)


if __name__ == "__main__":
    asyncio.run(main())
