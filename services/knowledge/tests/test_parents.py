"""v5.13 #1 small-to-big：group_into_parents 純邏輯單元測試（輕量 CI，無重依賴）。"""
from __future__ import annotations

import sys
from pathlib import Path

_SVC = Path(__file__).resolve().parent.parent
if str(_SVC) not in sys.path:
    sys.path.insert(0, str(_SVC))

from app.core.chunking.parents import group_into_parents  # noqa: E402


def test_budget_grouping():
    # 4×600 字、上限 2048 → 0+1+2=1800 收一組，第 4 個再開一組
    assert group_into_parents(["x" * 600] * 4, 2048) == [[0, 1, 2], [3]]


def test_oversize_child_standalone():
    # 單一超長塊不硬切、自成一組
    assert group_into_parents(["x" * 5000, "y" * 100], 2048) == [[0], [1]]


def test_all_fit_one_parent():
    assert group_into_parents(["a", "b", "c"], 2048) == [[0, 1, 2]]


def test_empty():
    assert group_into_parents([], 2048) == []


def test_covers_every_child_once():
    g = group_into_parents(["x" * 300] * 10, 1000)
    flat = [i for grp in g for i in grp]
    assert flat == list(range(10))  # 順序、不重不漏
