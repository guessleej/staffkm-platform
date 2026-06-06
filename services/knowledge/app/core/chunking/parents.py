"""v5.13 #1 small-to-big：把連續的 child 塊分組成 parent 塊（純邏輯、可輕量 CI 單測）。

策略：依字元預算累積連續 child，達 parent_size 即切一個 parent。回傳每個 parent 的 child 索引清單。
- 不打亂順序、不跨文件（呼叫端一份文件一次）。
- 單一 child 本身就超過 parent_size → 自成一個 parent（不硬切，保語意完整）。
"""
from __future__ import annotations


def group_into_parents(child_texts: list[str], parent_size: int) -> list[list[int]]:
    """回傳 parent 分組：[[child_idx,...], ...]，順序與輸入一致、涵蓋全部 child 一次。"""
    groups: list[list[int]] = []
    cur: list[int] = []
    cur_len = 0
    for i, t in enumerate(child_texts):
        tl = len(t or "")
        # 已有累積且再加會超界 → 先收掉目前這組（單一超長 child 不會在此被拆）
        if cur and cur_len + tl > parent_size:
            groups.append(cur)
            cur = []
            cur_len = 0
        cur.append(i)
        cur_len += tl
    if cur:
        groups.append(cur)
    return groups
