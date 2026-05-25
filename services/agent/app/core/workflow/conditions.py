"""Workflow condition 節點的純邏輯（從 executor 抽出 → 可在輕量 CI 單測）。

給定 config（variable/operator/value）+ context（變數值 dict）→ bool。無 DB / 無重依賴。
MaxKB v2 對齊：contains/equals/not_equal/not_empty/is_empty/regex_match/wildcard_match。
"""
from __future__ import annotations

import re

import structlog

log = structlog.get_logger()


def eval_condition(config: dict, context: dict) -> bool:
    """評估單一 condition 節點。未知 operator / 缺變數 → False（保守，不誤走 true_branch）。"""
    variable = config.get("variable", "")
    operator = config.get("operator", "contains")
    value = config.get("value", "")
    actual = str(context.get(variable, ""))
    if operator == "contains":
        return value in actual
    elif operator == "equals":
        return actual == value
    elif operator == "not_equal":
        return actual != value
    elif operator == "not_empty":
        return bool(actual.strip())
    elif operator == "is_empty":
        return not bool(actual.strip())
    elif operator == "regex_match":
        try:
            return bool(re.search(str(value), actual))
        except re.error as e:  # pattern 無效 → 視為不匹配
            log.warning("condition_regex_invalid", pattern=str(value), error=str(e))
            return False
    elif operator == "wildcard_match":
        import fnmatch
        return fnmatch.fnmatch(actual, str(value))
    return False
