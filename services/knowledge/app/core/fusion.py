"""RFC-014 GraphRAG 召回融合 — 純邏輯（無 DB / 無重型 deps，可在輕量 CI 單測）。

從 app.api.search 抽出，讓 test_search_fusion.py 不必 import fastapi/sqlalchemy 一票重依賴。
"""
from __future__ import annotations

# graph 召回作為 RRF 第三路的權重（等同一條完整召回來源）。
# ⚠ 別調低：A/B 實證 W≤0.5 時 graph-only 進不了 top-k → graph 增益整個歸零（見 CLAUDE.md §v5.11.4）。
_GRAPH_RRF_WEIGHT = 1.0


def fuse_multi_query(
    result_lists: list[list[dict]],
    top_k: int,
    rrf_k: int = 60,
) -> list[dict]:
    """v5.13 多查詢融合：把同一 KB 下「多個改寫查詢」各自的命中清單以 RRF 合併。

    - 每個段落最終分數 = Σ 1/(rrf_k + 該段在各清單的名次)；多查詢都命中者分數疊加（共識）。
    - 回傳的 row 是「命中該段、vector_score 最高那筆」的 copy，score 換成融合 RRF 值。
    - 單一清單（未展開）等價於照原排名輸出（呼叫端在 1 查詢時應自行短路省去開銷）。
    """
    agg: dict[str, dict] = {}  # pid -> {"row": best_row, "rrf": float}
    for results in result_lists:
        ranked = sorted(results, key=lambda x: float(x.get("score") or 0.0), reverse=True)
        for rank, r in enumerate(ranked, start=1):
            pid = str(r["id"])
            contrib = 1.0 / (rrf_k + rank)
            e = agg.get(pid)
            if e is None:
                agg[pid] = {"row": r, "rrf": contrib}
            else:
                e["rrf"] += contrib
                if float(r.get("vector_score") or 0.0) > float(e["row"].get("vector_score") or 0.0):
                    e["row"] = r
    merged: list[dict] = []
    for e in agg.values():
        row = dict(e["row"])
        row["score"] = e["rrf"]
        merged.append(row)
    merged.sort(key=lambda x: x["score"], reverse=True)
    return merged[:top_k]


def _fuse_graph_results(
    all_results: list[dict],
    g_rows: list[dict],
    rrf_k: int,
    graph_only_min_cosine: float,
) -> None:
    """graph 召回融合（RRF 第三路；**就地修改** all_results）。

    - hybrid∩graph（兩路都命中）：score += _GRAPH_RRF_WEIGHT/(rrf_k+idx)。共識加成，純加分。
      ⚠ by_id 必須持有 all_results 的「同一物件 ref」（非 copy），否則 boost 寫進孤兒物件、排序拿不到
        → 正確命中會被低分 graph-only 擠掉（曾在外部 A/B harness 重現此假性退步）。
    - graph-only（hybrid 完全沒命中）：以同權重併入做補召回，但須 cosine ≥ graph_only_min_cosine，
      濾掉低相關 graph-only（A/B 實證：門檻=0.5 增益全保、且不讓噪音段落擠掉 hybrid 命中）。
    """
    if not g_rows:
        return
    g_rows = sorted(g_rows, key=lambda r: r["score"], reverse=True)  # 按 cosine 排 → 定 RRF idx
    by_id = {str(r["id"]): r for r in all_results}  # 同 ref，boost 才會落在被排序的物件上
    for idx, gr in enumerate(g_rows):
        pid = str(gr["id"])
        contrib = _GRAPH_RRF_WEIGHT / (rrf_k + idx)
        if pid in by_id:
            # hybrid_search 的 score 可能是 Decimal（PG numeric）→ 轉 float 再加
            by_id[pid]["score"] = float(by_id[pid].get("score") or 0.0) + contrib
        elif float(gr.get("vector_score") or 0.0) >= graph_only_min_cosine:
            gr = dict(gr)
            gr["score"] = contrib
            all_results.append(gr)
            by_id[pid] = gr
