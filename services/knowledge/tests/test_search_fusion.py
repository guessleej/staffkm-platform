"""_fuse_graph_results 純邏輯單元測試（RFC-014 graph RRF 第三路融合）。

重點守住兩個曾踩過的雷：
1. 交集加分必須落在 all_results 的「同一物件 ref」上（外部 A/B harness 用 copy 導致 boost
   遺失、正確命中被低分 graph-only 擠掉 → 假性退步）。
2. graph-only 須通過 cosine 門檻才併入（低相關 graph-only 不得擠掉 hybrid 命中）。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SVC = Path(__file__).resolve().parent.parent  # services/knowledge
if str(_SVC) not in sys.path:
    sys.path.insert(0, str(_SVC))

from app.core.fusion import _GRAPH_RRF_WEIGHT, _fuse_graph_results  # noqa: E402

RRF_K = 60
FLOOR = 0.5


def test_intersection_boost_lands_on_same_object():
    """兩路皆命中 → boost 必須加到 all_results 內的物件（同 ref），否則排序拿不到。"""
    all_results = [{"id": "A", "score": 0.012}]
    g_rows = [{"id": "A", "score": 0.7, "vector_score": 0.7}]  # idx=0
    _fuse_graph_results(all_results, g_rows, RRF_K, FLOOR)
    assert len(all_results) == 1
    assert all_results[0]["score"] == pytest.approx(0.012 + _GRAPH_RRF_WEIGHT / RRF_K)


def test_graph_only_above_floor_inserted():
    all_results = [{"id": "A", "score": 0.012}]
    g_rows = [{"id": "B", "score": 0.60, "vector_score": 0.60}]  # ≥ 門檻 → 併入
    _fuse_graph_results(all_results, g_rows, RRF_K, FLOOR)
    by = {r["id"]: r for r in all_results}
    assert "B" in by
    assert by["B"]["score"] == pytest.approx(_GRAPH_RRF_WEIGHT / RRF_K)


def test_graph_only_below_floor_dropped():
    all_results = [{"id": "A", "score": 0.012}]
    g_rows = [{"id": "B", "score": 0.40, "vector_score": 0.40}]  # < 門檻 → 丟棄
    _fuse_graph_results(all_results, g_rows, RRF_K, FLOOR)
    assert [r["id"] for r in all_results] == ["A"]


def test_boosted_hit_not_displaced_by_graph_only_noise():
    """回歸守衛：被 graph 共識加分的正確命中，須穩贏 idx=0 的 graph-only 噪音段落。"""
    all_results = [{"id": "correct", "score": 0.012}]
    g_rows = [
        {"id": "noise", "score": 0.55, "vector_score": 0.55},     # graph-only, idx0, 過門檻
        {"id": "correct", "score": 0.50, "vector_score": 0.50},   # 交集, idx1, 被 boost
    ]
    _fuse_graph_results(all_results, g_rows, RRF_K, FLOOR)
    ranked = sorted(all_results, key=lambda r: r["score"], reverse=True)
    # correct = 0.012 + 1/61 ≈ 0.0284；noise = 1/60 ≈ 0.0167 → correct 在前
    assert ranked[0]["id"] == "correct"


def test_empty_graph_rows_noop():
    all_results = [{"id": "A", "score": 0.012}]
    _fuse_graph_results(all_results, [], RRF_K, FLOOR)
    assert all_results == [{"id": "A", "score": 0.012}]


# ════════════════════════════════════════════════════════════════════════════
# Retrieval 回歸 — 把 GraphRAG A/B 的兩個發現釘成確定性、每個 PR 都跑的守衛
# （live recall A/B 在 tools/eval/graphrag_ab.py + rag-eval.yml；這裡守融合的召回契約）
# ════════════════════════════════════════════════════════════════════════════

def _top_k_after_fusion(hybrid_hits, g_rows, k=5):
    """重現 search.py：融合 → 依 score 降序 dedupe → 取 top-k 的 id 序列。"""
    all_results = [dict(r) for r in hybrid_hits]
    _fuse_graph_results(all_results, g_rows, RRF_K, FLOOR)
    seen, ded = set(), []
    for r in sorted(all_results, key=lambda x: x["score"], reverse=True):
        pid = str(r["id"])
        if pid not in seen:
            seen.add(pid)
            ded.append(pid)
    return ded[:k]


def _recall(top, gt):
    return len(set(top) & gt) / min(len(gt), len(top))


def test_graph_lifts_recall_when_hybrid_misses_relevant():
    """『賺』：hybrid 漏掉的相關段落由 graph 錨定補回 → recall@5 提升。

    對應 A/B 實證：hybrid 候選池常漏掉公文實體段落（recall 低），graph 補召回。
    """
    gt = {"R1", "R2", "R3", "R4", "R5"}
    # hybrid top-5 只命中 R1，其餘是噪音 → recall@5 = 0.2（重現 A/B 的低 hybrid recall）
    hybrid = [
        {"id": "R1", "score": 0.020},
        {"id": "N1", "score": 0.005},
        {"id": "N2", "score": 0.004},
        {"id": "N3", "score": 0.003},
        {"id": "N4", "score": 0.002},
    ]
    # graph 錨定 hybrid 漏掉的相關段落（cosine 皆 ≥ 門檻）
    g_rows = [
        {"id": "R2", "score": 0.70, "vector_score": 0.70},
        {"id": "R3", "score": 0.66, "vector_score": 0.66},
        {"id": "R4", "score": 0.62, "vector_score": 0.62},
        {"id": "R5", "score": 0.58, "vector_score": 0.58},
    ]
    base_recall = _recall([h["id"] for h in hybrid], gt)
    fused_top = _top_k_after_fusion(hybrid, g_rows, 5)
    fused_recall = _recall(fused_top, gt)
    assert base_recall == 0.2
    assert fused_recall > base_recall, "graph 未提升 recall（補召回失效，疑 ivfflat.probes/門檻回歸）"
    assert fused_recall >= 0.8, f"graph 補召回不足：fused recall@5={fused_recall}"
    assert "R1" in fused_top, "強 hybrid 命中 R1 被擠出 top-5（不該）"


def test_low_cosine_graph_noise_does_not_displace_relevant():
    """『不退』：低 cosine 的 graph-only 噪音（< 門檻）須被濾掉，不得擠掉 hybrid 的正確命中。

    這正是 v5.11.4 cosine 門檻的職責 —— 移除/調低門檻 → 此測試紅。
    """
    gt = {"R1", "R2", "R3", "R4", "R5"}
    hybrid = [   # hybrid top-5 全中 → recall@5 = 1.0
        {"id": "R1", "score": 0.020},
        {"id": "R2", "score": 0.018},
        {"id": "R3", "score": 0.016},
        {"id": "R4", "score": 0.014},
        {"id": "R5", "score": 0.012},
    ]
    g_rows = [{"id": "NOISE", "score": 0.40, "vector_score": 0.40}]  # < 0.5 門檻 → 應丟棄
    fused_top = _top_k_after_fusion(hybrid, g_rows, 5)
    assert _recall(fused_top, gt) == 1.0, "低相關 graph-only 噪音擠掉了正確命中（門檻回歸）"
    assert "NOISE" not in fused_top


def test_graph_consensus_boost_keeps_relevant_on_top():
    """『不退·共識』：兩路皆命中的相關段落被 boost 後，穩居 top-5（不被其他 graph-only 擠掉）。"""
    gt = {"R1", "R2"}
    hybrid = [{"id": "R1", "score": 0.012}, {"id": "R2", "score": 0.011}]
    g_rows = [
        {"id": "R1", "score": 0.70, "vector_score": 0.70},   # 交集 → boost
        {"id": "R2", "score": 0.66, "vector_score": 0.66},   # 交集 → boost
        {"id": "G1", "score": 0.60, "vector_score": 0.60},   # graph-only 過門檻
    ]
    fused_top = _top_k_after_fusion(hybrid, g_rows, 5)
    assert _recall(fused_top[:2], gt) == 1.0, "被 boost 的相關命中未穩居前列"
