"""CRDT primitives — v5.0 K (reference implementation only).

v5.0 只交 LWW-Register + G-Counter stub。
v5.x 計畫補：
  - v5.2: 真實 G-Counter / PN-Counter（per-region keyed map），接到
          user_quotas + model_usage_logs 跨 region merge
  - v5.3: OR-Set（observed-remove set）for tags
  - v5.4: LWW-Register w/ Hybrid Logical Clock（HLC）取代 wall clock

⚠️ 這個檔目前 **不被 hot path 引用** — 純 reference。等 v5.2 真的接 cost
ledger merge 時才會進 production 路徑。
"""
from __future__ import annotations
import json
from typing import Any


def lww_resolve(
    value_a: Any,
    value_b: Any,
    ts_a: float,
    ts_b: float,
) -> tuple[Any, str]:
    """LWW (Last-Write-Wins) Register 衝突解決。

    Returns (resolved_value, source) — source in {'a', 'b'}。

    Tie-break：timestamp 相同時用 serialized 字典序（deterministic across nodes）。

    ⚠️ 仰賴可信時間源。Wall clock skew 會 silently 吃掉寫入。v5.4 要換 HLC。
    """
    if ts_a > ts_b:
        return value_a, "a"
    if ts_b > ts_a:
        return value_b, "b"
    sa = json.dumps(value_a, sort_keys=True, default=str)
    sb = json.dumps(value_b, sort_keys=True, default=str)
    if sa <= sb:
        return value_a, "a"
    return value_b, "b"


def gcounter_merge(counts_by_region: dict[str, int]) -> int:
    """G-Counter（grow-only counter）merge。

    真實 G-Counter 是 region-keyed map，merge 取每個 key 的 max、最後 sum。
    v5.0 這個 stub 假設 input 已是「該 region 的 current count」，直接 sum。
    Real impl 要存 per-region high-water mark（v5.2 補）。

    Example:
        # us-east: quota.used = 12; eu-west: quota.used = 8
        gcounter_merge({"us-east-1": 12, "eu-west-1": 8})  # → 20
    """
    if not counts_by_region:
        return 0
    return sum(max(0, int(v)) for v in counts_by_region.values())


def gcounter_increment(
    state: dict[str, int],
    region_id: str,
    delta: int = 1,
) -> dict[str, int]:
    """G-Counter local increment。Returns new state（不 mutate input）。"""
    if delta < 0:
        raise ValueError("G-Counter only grows; use PN-Counter for decrement")
    new = dict(state)
    new[region_id] = new.get(region_id, 0) + delta
    return new
