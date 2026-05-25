"""workflow condition 節點純邏輯單元測試（分支走錯 = workflow 全錯，原本無守）。"""
from __future__ import annotations

import sys
from pathlib import Path

_SVC = Path(__file__).resolve().parent.parent  # services/agent
if str(_SVC) not in sys.path:
    sys.path.insert(0, str(_SVC))

from app.core.workflow.conditions import eval_condition  # noqa: E402


def _c(operator, value, variable="x"):
    return {"variable": variable, "operator": operator, "value": value}


def test_contains():
    assert eval_condition(_c("contains", "abc"), {"x": "xx abc yy"}) is True
    assert eval_condition(_c("contains", "zzz"), {"x": "xx abc yy"}) is False


def test_equals_and_not_equal():
    assert eval_condition(_c("equals", "5"), {"x": "5"}) is True
    assert eval_condition(_c("equals", "5"), {"x": "6"}) is False
    assert eval_condition(_c("not_equal", "5"), {"x": "6"}) is True
    assert eval_condition(_c("not_equal", "5"), {"x": "5"}) is False


def test_empty_checks():
    assert eval_condition(_c("not_empty", ""), {"x": "  hi "}) is True
    assert eval_condition(_c("not_empty", ""), {"x": "   "}) is False
    assert eval_condition(_c("is_empty", ""), {"x": ""}) is True
    assert eval_condition(_c("is_empty", ""), {"x": "hi"}) is False


def test_missing_variable_is_empty_string():
    # 缺變數 → actual="" → contains 非空值為 False、is_empty 為 True（保守）
    assert eval_condition(_c("contains", "a"), {}) is False
    assert eval_condition(_c("is_empty", ""), {}) is True


def test_regex_match_and_invalid_pattern():
    assert eval_condition(_c("regex_match", r"\d{3}"), {"x": "ab123"}) is True
    assert eval_condition(_c("regex_match", r"^z"), {"x": "ab123"}) is False
    # 無效 pattern → 不匹配（不可炸）
    assert eval_condition(_c("regex_match", r"([unclosed"), {"x": "anything"}) is False


def test_wildcard_match():
    assert eval_condition(_c("wildcard_match", "臺教*字第*號"), {"x": "臺教大字第1120001234號"}) is True
    assert eval_condition(_c("wildcard_match", "abc?"), {"x": "abcd"}) is True
    assert eval_condition(_c("wildcard_match", "abc?"), {"x": "abcde"}) is False


def test_unknown_operator_false():
    # 未知 operator → False（保守，不誤走 true_branch）
    assert eval_condition(_c("greater_than", "5"), {"x": "9"}) is False
