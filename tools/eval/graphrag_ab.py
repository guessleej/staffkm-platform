"""GraphRAG A/B：台灣公文「完整語料」KB，hybrid baseline vs hybrid+graph 融合的 recall@5 對比。

忠實版：直接 import 真實 search.py 的 `_fuse_graph_results`（不重寫融合邏輯），
ground-truth 用 kb_entity_mentions（query→實體名→其 mentions 段落集）。

跑法（在 knowledge 容器內，source 已掛載）：
    docker cp tools/eval/graphrag_ab.py staffkm-knowledge:/app/graphrag_ab.py
    docker exec staffkm-knowledge python graphrag_ab.py

目的：確認 ivfflat.probes 修正 + graph-only cosine 門檻後
「賺的題目維持增益、退步的題目不再退步」。
"""
import asyncio

from app.config import settings
from staffkm_core.utils.database import init_db

init_db(settings.DB_URL)
from sqlalchemy import text  # noqa: E402

from app.core.fusion import _fuse_graph_results  # 真實融合邏輯  # noqa: E402
from app.core.embedder import get_embedder  # noqa: E402
from app.core.graph import graph_anchored_paragraph_ids  # noqa: E402
from app.api.search import _score_paragraphs_by_ids  # noqa: E402
from app.core.vectorstore import hybrid_search  # noqa: E402
from staffkm_core.utils import database as _db  # noqa: E402

KB = "f3281a2b-b90f-4451-b0c5-25b40b9d5054"
RRF_K = 60
SIM_THRESHOLD = 0.5  # = SearchRequest.similarity_threshold 預設；graph-only cosine 門檻

# query → 對應的 ground-truth 實體名（用其 mentions 當相關段落集）
CASES = [
    ("陸生來臺就學申請的法源依據", ["《大陸地區人民來臺就讀專科以上學校辦法》"]),
    ("學位授予的法律依據與規定",   ["学位授予法", "高等教育法"]),
    ("性別平等教育委員會如何進行調查", ["性別平等教育委員會", "性別平等教育法"]),
    ("學生獎懲與學術誠信規範",     ["學生獎懲辦法", "學術誠信"]),
    ("教育部高等教育司的職掌業務", ["教育部高等教育司"]),
]


async def gt_paras(session, names):
    rows = await session.execute(text("""
        SELECT DISTINCT m.paragraph_id
        FROM kb_entities e JOIN kb_entity_mentions m ON m.entity_id = e.id
        WHERE e.knowledge_base_id = CAST(:kb AS uuid) AND e.name = ANY(:names)
    """), {"kb": KB, "names": names})
    return {str(r[0]) for r in rows.fetchall()}


def merged_top(hybrid_hits, g_rows, k=5):
    """複製 search.py 的融合 + dedupe 取 top-k（呼叫真實 _fuse_graph_results）。"""
    all_results = [dict(r) for r in hybrid_hits]
    _fuse_graph_results(all_results, g_rows, RRF_K, SIM_THRESHOLD)
    seen, ded = set(), []
    for r in sorted(all_results, key=lambda x: x["score"], reverse=True):
        pid = str(r["id"])
        if pid not in seen:
            seen.add(pid)
            ded.append(r)
    return [str(r["id"]) for r in ded[:k]]


def recall(top, gt):
    if not gt:
        return None
    return len(set(top) & gt) / min(len(gt), len(top)) if top else 0.0


async def main():
    emb = get_embedder(settings.EMBEDDING_MODEL, settings.OPENAI_API_KEY, settings.EMBEDDING_BASE_URL or None)
    async with _db._session_factory() as s:
        print(f"probes={settings.IVFFLAT_PROBES}  graph-only cosine 門檻={SIM_THRESHOLD}")
        print(f"{'查詢':<22} | GT | hyb@5命中 | base@5 | graph@5 |")
        print("-" * 70)
        base_sum = graph_sum = n = 0
        regressions = []
        for q, names in CASES:
            qe = await emb.embed_text(q)
            gt = await gt_paras(s, names)
            hyb5 = await hybrid_search(session=s, kb_id=KB, query_embedding=qe, query_text=q, top_k=5)
            g_pids = await graph_anchored_paragraph_ids(s, [KB], qe, settings.GRAPH_QUERY_TOP_ENTITIES)
            g_rows = await _score_paragraphs_by_ids(s, g_pids, qe)
            base5 = [str(h["id"]) for h in hyb5]
            graph5 = merged_top(hyb5, g_rows, 5)
            rb, rg = recall(base5, gt), recall(graph5, gt)
            base_sum += rb
            graph_sum += rg
            n += 1
            if rg < rb - 1e-9:
                regressions.append((q[:18], round(rb, 2), round(rg, 2)))
            flag = "  ⬇退步" if rg < rb - 1e-9 else ("  ⬆" if rg > rb + 1e-9 else "")
            print(f"{q[:20]:<20} | {len(gt):>2} | {len(set(base5) & gt):>7} | {rb:.2f}   | {rg:.2f}   |{flag}")
        print("-" * 70)
        print(f"平均 base@5={base_sum / n:.3f}  graph@5={graph_sum / n:.3f}  退步題={len(regressions)} {regressions}")


if __name__ == "__main__":
    asyncio.run(main())
