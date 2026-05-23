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

from app.api.search import _GRAPH_RRF_WEIGHT, _fuse_graph_results  # noqa: E402

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
