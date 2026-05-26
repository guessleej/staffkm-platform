"""CRDT 衝突解決 primitive 單元測試（active-active 正確性核心；純邏輯、輕量 CI）。

`app.core.crdt` 目前是 reference impl（v5.2 才接 cost ledger merge 進 hot path），但它是
active-active「衝突怎麼解」的語意根基——先把語意用測試釘死，等真接上時不會走鐘：
- LWW：時間大者勝；**時間相同必須 deterministic**（跨節點同結果，否則 split-brain）。
- G-Counter：grow-only，merge 取和、increment 不可 mutate input、不可減。
純函式、無 DB／無重依賴 → 跟 conditions/secrets 同層，輕量 backend job 就能跑。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SVC = Path(__file__).resolve().parent.parent  # services/agent
if str(_SVC) not in sys.path:
    sys.path.insert(0, str(_SVC))

from app.core.crdt import gcounter_increment, gcounter_merge, lww_resolve  # noqa: E402


# ── LWW-Register ─────────────────────────────────────────────────────────
def test_lww_newer_timestamp_wins():
    assert lww_resolve("old", "new", 1.0, 2.0) == ("new", "b")
    assert lww_resolve("new", "old", 2.0, 1.0) == ("new", "a")


def test_lww_tie_is_deterministic_lexicographic():
    # 時間相同 → 用序列化字典序決勝，且**兩個方向呼叫結果一致**（跨節點收斂）
    v1, s1 = lww_resolve("apple", "banana", 5.0, 5.0)
    v2, s2 = lww_resolve("banana", "apple", 5.0, 5.0)
    assert v1 == "apple" and v2 == "apple"   # 字典序小者（apple）恆勝，與參數順序無關


def test_lww_tie_dict_values_deterministic():
    a = {"x": 1, "y": 2}
    b = {"x": 1, "y": 3}
    # sort_keys 序列化 → 同一筆恆勝，不受 dict 插入順序影響
    r_ab, _ = lww_resolve(a, b, 9.0, 9.0)
    r_ba, _ = lww_resolve(b, a, 9.0, 9.0)
    assert r_ab == r_ba


# ── G-Counter ────────────────────────────────────────────────────────────
def test_gcounter_merge_sums_regions():
    assert gcounter_merge({"us-east-1": 12, "eu-west-1": 8}) == 20


def test_gcounter_merge_empty_is_zero():
    assert gcounter_merge({}) == 0


def test_gcounter_merge_clamps_negative():
    # 防呆：負值視為 0（grow-only 不該出現負，但不可被污染成負總和）
    assert gcounter_merge({"a": 5, "b": -3}) == 5


def test_gcounter_increment_does_not_mutate_input():
    state = {"us-east-1": 5}
    new = gcounter_increment(state, "us-east-1", 3)
    assert new == {"us-east-1": 8}
    assert state == {"us-east-1": 5}   # 原 state 不變（避免別處共用 ref 被改）


def test_gcounter_increment_new_region():
    assert gcounter_increment({}, "eu-west-1") == {"eu-west-1": 1}


def test_gcounter_increment_rejects_decrement():
    with pytest.raises(ValueError, match="only grows"):
        gcounter_increment({"a": 1}, "a", -1)
