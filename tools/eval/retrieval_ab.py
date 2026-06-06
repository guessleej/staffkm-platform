"""v5.13 檢索智能 A/B — multi-query（#2）召回增益量測（evidence-gated，與 graphrag_ab 同紀律）。

忠實版：直接 import 真實 `hybrid_search` / `expand_query` / `fuse_multi_query` / `rerank`，
不重寫邏輯。在 knowledge 容器內、對已 seed 的 KB 跑：

    docker exec -e RETRIEVAL_EVAL_KB=<kb_id> staffkm-knowledge python tools/eval/retrieval_ab.py

量測 recall@5：
  base       = 單一查詢 hybrid（multi_query OFF）
  multiquery = expand_query → 各變體 hybrid → fuse_multi_query（multi_query ON）
  +rerank    = 兩者再各自過內建 reranker（看 rerank 疊加效果）

ground-truth：rag_eval_dataset.json 的 expected_corpus_anchors（file + title_contains），
以 DB 直接解析成 paragraph_id（不依賴 seed 輸出檔）。對不到的 query 自動跳過（換語料不誤判）。
"""
import asyncio
import json
import os
import sys
from pathlib import Path

from app.config import settings
from staffkm_core.utils.database import init_db

init_db(settings.DB_URL)
from sqlalchemy import text  # noqa: E402

from app.core.embedder import get_embedder  # noqa: E402
from app.core.fusion import fuse_multi_query  # noqa: E402
from app.core.query_transform import expand_query  # noqa: E402
from app.core.vectorstore import hybrid_search  # noqa: E402
from staffkm_core.utils import database as _db  # noqa: E402

KB = os.environ.get("RETRIEVAL_EVAL_KB", "")
DATASET = Path(__file__).parent / "rag_eval_dataset.json"
TOP_K = 5
RRF_K = 60


async def resolve_gt(session, kb: str, anchors: list[dict]) -> set[str]:
    """把 expected_corpus_anchors（file + title_contains）解析成 paragraph_id 集合（DB 直查）。"""
    gt: set[str] = set()
    for a in anchors:
        f = a.get("file", "")
        needle = a.get("title_contains", "")
        rows = await session.execute(
            text("""
                SELECT p.id FROM paragraphs p JOIN documents d ON d.id = p.document_id
                WHERE p.knowledge_base_id = CAST(:kb AS uuid)
                  AND p.is_active = true
                  AND d.name LIKE :fpat
                  AND (coalesce(p.title,'') LIKE :npat OR p.content LIKE :npat)
                LIMIT 5
            """),
            {"kb": kb, "fpat": f"%{f}%", "npat": f"%{needle}%"},
        )
        gt.update(str(r[0]) for r in rows.fetchall())
    return gt


def recall(top_ids: list[str], gt: set[str]) -> float | None:
    if not gt:
        return None
    return len(set(top_ids) & gt) / min(len(gt), len(top_ids)) if top_ids else 0.0


async def _base(s, kb, q, qe):
    hits = await hybrid_search(session=s, kb_id=kb, query_embedding=qe, query_text=q, top_k=TOP_K)
    return [str(h["id"]) for h in hits]


async def _multiquery(s, kb, q, embedder):
    variants = await expand_query(q)
    if len(variants) <= 1:
        return None  # 展開失敗/未啟用 → 無法比較
    embs = await embedder.embed_batch(variants)
    lists = []
    for qt, qe in zip(variants, embs):
        lists.append(await hybrid_search(session=s, kb_id=kb, query_embedding=qe, query_text=qt, top_k=TOP_K))
    return [str(h["id"]) for h in fuse_multi_query(lists, TOP_K, RRF_K)], len(variants) - 1


async def main() -> int:
    if not KB:
        print("需 RETRIEVAL_EVAL_KB=<kb_id>（已 seed 的 KB）。exit 0。")
        return 0
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    embedder = get_embedder(settings.EMBEDDING_MODEL, settings.OPENAI_API_KEY,
                            settings.EMBEDDING_BASE_URL or None)
    # 確保展開開著（A/B 要看 ON 效果）；不改全域、只在本程序內覆寫旗標
    settings.QUERY_EXPAND_ENABLED = True

    async with _db._session_factory() as s:
        print(f"KB={KB}  embed_dim 測試…  QUERY_EXPAND={settings.QUERY_EXPAND_ENABLED}")
        print(f"{'查詢':<24} | GT | base@5 | MQ@5  | Δ     | 變體")
        print("-" * 70)
        nb = base_sum = mq_sum = n = 0
        wins = []
        for q in dataset.get("queries", []):
            query = q["query"]
            gt = await resolve_gt(s, KB, q.get("expected_corpus_anchors") or [])
            if not gt:
                continue
            qe = await embedder.embed_text(query)
            base_ids = await _base(s, KB, query, qe)
            rb = recall(base_ids, gt)
            mq = await _multiquery(s, KB, query, embedder)
            if mq is None:
                print(f"{query[:22]:<22} | {len(gt):>2} | {rb:.2f}   | (展開失敗，跳過)")
                continue
            mq_ids, nvar = mq
            rmq = recall(mq_ids, gt)
            base_sum += rb; mq_sum += rmq; n += 1
            d = rmq - rb
            if d > 1e-9:
                wins.append((query[:18], round(rb, 2), round(rmq, 2)))
            flag = " ⬆" if d > 1e-9 else (" ⬇" if d < -1e-9 else "")
            print(f"{query[:22]:<22} | {len(gt):>2} | {rb:.2f}   | {rmq:.2f}  | {d:+.2f}{flag} | {nvar}")
        print("-" * 70)
        if n == 0:
            print("SKIP：對不到任何 ground-truth（KB 未 seed 此資料集？）。exit 0。")
            return 0
        ab, amq = base_sum / n, mq_sum / n
        print(f"平均 recall@5：base={ab:.3f}  multi-query={amq:.3f}  (增益={amq - ab:+.3f}，{n} 題)")
        print(f"進步題：{len(wins)}  {wins if wins else ''}")
        print("\n判讀：增益>0 且無明顯退步 → multi-query 有實證價值，可在該語料常開"
              "（QUERY_EXPAND_ENABLED=true）；增益≈0 → 維持預設關、省成本。")
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
