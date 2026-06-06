"""v5.13 多查詢：fuse_multi_query（RRF 融合）+ query_transform._parse_list 純邏輯單元測試。

輕量 CI 可跑：fusion 無重依賴；query_transform._parse_list 是純字串解析（不觸發 openai 連線）。
"""
from __future__ import annotations

import sys
from pathlib import Path

_SVC = Path(__file__).resolve().parent.parent  # services/knowledge
if str(_SVC) not in sys.path:
    sys.path.insert(0, str(_SVC))

from app.core.fusion import fuse_multi_query  # noqa: E402
from app.core.query_transform import _parse_list  # noqa: E402

RRF_K = 60


# ── fuse_multi_query ────────────────────────────────────────────────

def test_consensus_paragraph_ranks_first():
    """多個查詢都命中的段落（共識）分數應疊加 → 排第一。"""
    list_a = [{"id": "X", "score": 0.9, "vector_score": 0.9},
              {"id": "Y", "score": 0.8, "vector_score": 0.8}]
    list_b = [{"id": "X", "score": 0.7, "vector_score": 0.7},
              {"id": "Z", "score": 0.6, "vector_score": 0.6}]
    out = fuse_multi_query([list_a, list_b], top_k=5, rrf_k=RRF_K)
    assert out[0]["id"] == "X"  # 兩清單都命中 → RRF 疊加最高
    # X = 1/(60+1)+1/(60+1)；Y/Z 各只一條 1/(60+2)
    assert out[0]["score"] > out[1]["score"]


def test_single_list_preserves_order():
    """單一清單 → 等價於照名次輸出（不打亂）。"""
    one = [{"id": "A", "score": 0.9}, {"id": "B", "score": 0.5}, {"id": "C", "score": 0.1}]
    out = fuse_multi_query([one], top_k=5, rrf_k=RRF_K)
    assert [r["id"] for r in out] == ["A", "B", "C"]


def test_top_k_truncates():
    lists = [[{"id": str(i), "score": 1.0 - i * 0.1} for i in range(6)]]
    out = fuse_multi_query(lists, top_k=3, rrf_k=RRF_K)
    assert len(out) == 3


def test_keeps_higher_vector_score_metadata():
    """同段在不同清單出現 → 保留 vector_score 較高那筆的 metadata。"""
    la = [{"id": "X", "score": 0.5, "vector_score": 0.4, "content": "low"}]
    lb = [{"id": "X", "score": 0.5, "vector_score": 0.9, "content": "high"}]
    out = fuse_multi_query([la, lb], top_k=1, rrf_k=RRF_K)
    assert out[0]["content"] == "high"


def test_empty_lists():
    assert fuse_multi_query([], top_k=5) == []
    assert fuse_multi_query([[], []], top_k=5) == []


# ── _parse_list（LLM 改寫回應解析）──────────────────────────────────

def test_parse_json_array():
    assert _parse_list('["請假規定", "休假辦法"]') == ["請假規定", "休假辦法"]


def test_parse_json_with_fence():
    assert _parse_list('```json\n["甲", "乙"]\n```') == ["甲", "乙"]


def test_parse_json_embedded_in_prose():
    assert _parse_list('好的，以下是改寫：["A問", "B問"] 希望有幫助') == ["A問", "B問"]


def test_parse_line_fallback():
    raw = "1. 第一個改寫\n2. 第二個改寫\n- 第三個"
    assert _parse_list(raw) == ["第一個改寫", "第二個改寫", "第三個"]


def test_parse_empty():
    assert _parse_list("") == []
    assert _parse_list("   ") == []
