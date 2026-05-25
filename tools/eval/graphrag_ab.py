"""GraphRAG A/B retrieval 回歸：hybrid baseline vs hybrid+graph 融合的 recall@5。

忠實版：直接 import 真實 search.py 的 `_fuse_graph_results`（不重寫融合邏輯），
ground-truth 用 kb_entity_mentions（query→實體名→其 mentions 段落集）。

**這是回歸 GATE（非只報表）**：
- 無 graph 資料（KB 不存在 / 0 entities）→ SKIP，exit 0（fresh stack 不誤殺）。
- 有資料 → 斷言「賺的維持、退的不退」：
    1. 平均 graph@5 ≥ 平均 base@5（graph 整體不得降低 recall）
    2. 任何單題 graph@5 ≥ base@5 − EPS（沒有單題退步，守 v5.11.4 cosine 門檻/probes）
  違反 → exit 1（CI 紅）。

跑法（knowledge 容器內，source 已掛載）：
    docker exec -e GRAPH_EVAL_KB=<kb_id> staffkm-knowledge python tools/eval/graphrag_ab.py
KB 由環境變數 GRAPH_EVAL_KB 指定（預設「完整語料」）。
"""
import asyncio
import os
import sys

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

KB = os.environ.get("GRAPH_EVAL_KB", "f3281a2b-b90f-4451-b0c5-25b40b9d5054")
RRF_K = 60
SIM_THRESHOLD = 0.5  # = SearchRequest.similarity_threshold 預設；graph-only cosine 門檻
REGRESSION_EPS = 1e-9  # 單題容忍度（嚴格：不允許任何退步）

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


async def build_cases(session) -> list[tuple[str, list[str]]]:
    """決定要跑哪些 query→entity。

    優先用上面策劃的台灣公文 CASES（若該 KB 有這些實體）；否則自動從 KB 實際實體
    （mentions ≥ 2）衍生 query=實體名、gt=其 mentions → 讓本 gate 能在任何 graph KB
    （含 seed 語料）上運作，不綁死特定語料。
    """
    present = []
    for q, names in CASES:
        if await gt_paras(session, names):
            present.append((q, names))
    if present:
        return present
    rows = await session.execute(text("""
        SELECT e.name FROM kb_entities e JOIN kb_entity_mentions m ON m.entity_id = e.id
        WHERE e.knowledge_base_id = CAST(:kb AS uuid)
        GROUP BY e.name HAVING count(m.paragraph_id) >= 2
        ORDER BY count(m.paragraph_id) DESC LIMIT 8
    """), {"kb": KB})
    return [(name, [name]) for (name,) in rows.fetchall()]


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


async def _has_graph_data(session) -> bool:
    r = await session.execute(
        text("SELECT count(*) FROM kb_entities WHERE knowledge_base_id = CAST(:kb AS uuid)"),
        {"kb": KB},
    )
    return (r.scalar() or 0) > 0


async def main() -> int:
    emb = get_embedder(settings.EMBEDDING_MODEL, settings.OPENAI_API_KEY, settings.EMBEDDING_BASE_URL or None)
    async with _db._session_factory() as s:
        if not await _has_graph_data(s):
            print(f"SKIP：KB {KB} 無 graph 資料（0 entities）→ 此回歸需先 seed+建圖。exit 0。")
            return 0
        print(f"probes={settings.IVFFLAT_PROBES}  graph-only cosine 門檻={SIM_THRESHOLD}  KB={KB}")
        print(f"{'查詢':<22} | GT | hyb@5命中 | base@5 | graph@5 |")
        print("-" * 70)
        cases = await build_cases(s)
        base_sum = graph_sum = n = 0
        regressions = []
        for q, names in cases:
            qe = await emb.embed_text(q)
            gt = await gt_paras(s, names)
            if not gt:
                continue  # 此 KB 沒有該實體 → 跳過該題（換 KB 時不誤判）
            hyb5 = await hybrid_search(session=s, kb_id=KB, query_embedding=qe, query_text=q, top_k=5)
            g_pids = await graph_anchored_paragraph_ids(s, [KB], qe, settings.GRAPH_QUERY_TOP_ENTITIES)
            g_rows = await _score_paragraphs_by_ids(s, g_pids, qe)
            base5 = [str(h["id"]) for h in hyb5]
            graph5 = merged_top(hyb5, g_rows, 5)
            rb, rg = recall(base5, gt), recall(graph5, gt)
            base_sum += rb
            graph_sum += rg
            n += 1
            if rg < rb - REGRESSION_EPS:
                regressions.append((q[:18], round(rb, 2), round(rg, 2)))
            flag = "  ⬇退步" if rg < rb - REGRESSION_EPS else ("  ⬆" if rg > rb + 1e-9 else "")
            print(f"{q[:20]:<20} | {len(gt):>2} | {len(set(base5) & gt):>7} | {rb:.2f}   | {rg:.2f}   |{flag}")
        print("-" * 70)
        if n == 0:
            print("SKIP：此 KB 對不到任何 ground-truth 實體 → exit 0。")
            return 0
        avg_base, avg_graph = base_sum / n, graph_sum / n
        print(f"平均 base@5={avg_base:.3f}  graph@5={avg_graph:.3f}  退步題={len(regressions)} {regressions}")

        # ── 回歸 GATE ──────────────────────────────────────────────
        failures = []
        if avg_graph < avg_base - REGRESSION_EPS:
            failures.append(f"整體 recall 退步：graph {avg_graph:.3f} < hybrid {avg_base:.3f}")
        if regressions:
            failures.append(f"單題退步 {len(regressions)} 題：{regressions}（守 v5.11.4 cosine 門檻/probes）")
        if failures:
            print("❌ GraphRAG retrieval 回歸：\n  - " + "\n  - ".join(failures))
            return 1
        print("✅ GraphRAG retrieval 回歸通過：graph 不低於 hybrid、且無單題退步。")
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
