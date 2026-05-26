"""Workflow executor 編排核心整合測試（真 PostgreSQL）。

守的是「workflow 跑錯 = 全錯」的編排骨幹（不碰 LLM / 外部服務的節點）：
- 主迴圈走訪 + condition 分支路由（走錯分支 → 整條 workflow 結果錯）
- `workflow_run_steps` 持久化（run_id / step_index 遞增 / status / node_key 順序）
- input_snapshot 的 `CAST(:inp AS jsonb)` 真 round-trip（CLAUDE.md §8 dialect 雷的活靶）
- 無 run_id → 不落 step（dev/unit 友善 noop）
- disabled 節點 → 跳過且不落 step

executor.py 巨大（40+ node_type，多數要外部 LLM/服務）→ 本檔只覆蓋「LLM-free 編排
核心」：start / variable / condition / answer + _record_step + 走訪/路由。coverage gate
按此誠實設定（不假裝整個 executor 都測了）。
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.core.workflow.executor import WorkflowExecutor

pytestmark = pytest.mark.asyncio


def _graph():
    """start → variable(score=user_input) → condition(score contains 'urgent')
    → true:ans_urgent / false:ans_normal。"""
    nodes = [
        {"node_key": "start", "node_type": "start", "config": {}},
        {"node_key": "setvar", "node_type": "variable",
         "config": {"assignments": [{"name": "score", "value_expression": "{{user_input}}"}]}},
        {"node_key": "cond", "node_type": "condition",
         "config": {"variable": "score", "operator": "contains", "value": "urgent",
                    "true_branch": "ans_urgent", "false_branch": "ans_normal"}},
        {"node_key": "ans_urgent", "node_type": "answer", "config": {"content_template": "URGENT"}},
        {"node_key": "ans_normal", "node_type": "answer", "config": {"content_template": "normal"}},
    ]
    edges = [
        {"source_node_key": "start", "target_node_key": "setvar"},
        {"source_node_key": "setvar", "target_node_key": "cond"},
    ]
    return nodes, edges


async def _collect(wf, user_input):
    events = [ev async for ev in wf.execute(user_input)]
    answer = "".join(ev["data"] for ev in events if ev["event"] == "token")
    return events, answer


async def _steps(session, run_id):
    r = await session.execute(text(
        "SELECT step_index, node_key, node_type, status, input_snapshot "
        "FROM workflow_run_steps WHERE run_id = CAST(:r AS uuid) ORDER BY step_index"
    ), {"r": str(run_id)})
    return [dict(row._mapping) for row in r.fetchall()]


# ── condition 路由 + step 持久化 ─────────────────────────────────────────
async def test_true_branch_routing_and_step_persistence(db_session):
    run_id = uuid.uuid4()
    nodes, edges = _graph()
    wf = WorkflowExecutor(nodes, edges, run_id=run_id)

    _events, answer = await _collect(wf, "this is urgent please")
    assert answer == "URGENT"

    steps = await _steps(db_session, run_id)
    assert [s["node_key"] for s in steps] == ["start", "setvar", "cond", "ans_urgent"]
    assert [s["step_index"] for s in steps] == [0, 1, 2, 3]
    assert all(s["status"] == "ok" for s in steps)
    assert [s["node_type"] for s in steps] == ["start", "variable", "condition", "answer"]


async def test_false_branch_routing(db_session):
    run_id = uuid.uuid4()
    nodes, edges = _graph()
    wf = WorkflowExecutor(nodes, edges, run_id=run_id)

    _events, answer = await _collect(wf, "just a normal hello")
    assert answer == "normal"

    steps = await _steps(db_session, run_id)
    assert [s["node_key"] for s in steps] == ["start", "setvar", "cond", "ans_normal"]


# ── input_snapshot jsonb round-trip（CAST(:inp AS jsonb) 活靶）────────────
async def test_input_snapshot_jsonb_roundtrip(db_session):
    run_id = uuid.uuid4()
    nodes, edges = _graph()
    wf = WorkflowExecutor(nodes, edges, run_id=run_id)
    await _collect(wf, "urgent")

    steps = await _steps(db_session, run_id)
    cond_step = next(s for s in steps if s["node_key"] == "cond")
    # jsonb 存回為 dict，且內容＝節點 config（證明 CAST 寫入/讀出無損）
    assert cond_step["input_snapshot"]["operator"] == "contains"
    assert cond_step["input_snapshot"]["true_branch"] == "ans_urgent"


# ── 無 run_id → 不落 step（noop）──────────────────────────────────────────
async def test_no_run_id_skips_persistence(db_session):
    nodes, edges = _graph()
    wf = WorkflowExecutor(nodes, edges)  # 無 run_id
    _events, answer = await _collect(wf, "urgent")
    assert answer == "URGENT"  # 仍正常跑完

    count = (await db_session.execute(
        text("SELECT count(*) FROM workflow_run_steps"))).scalar()
    assert count == 0


# ── disabled 節點 → 跳過、不落 step ──────────────────────────────────────
async def test_disabled_node_skipped(db_session):
    run_id = uuid.uuid4()
    nodes, edges = _graph()
    for n in nodes:
        if n["node_key"] == "setvar":
            n["disabled"] = True
    wf = WorkflowExecutor(nodes, edges, run_id=run_id)
    events, _answer = await _collect(wf, "urgent")

    assert any(ev["event"] == "node_skipped" for ev in events)
    steps = await _steps(db_session, run_id)
    assert "setvar" not in [s["node_key"] for s in steps]


# ── 巢狀深度防護（防無窮遞迴 sub_workflow）────────────────────────────────
async def test_depth_guard_raises():
    nodes, edges = _graph()
    with pytest.raises(RuntimeError, match="depth exceeded"):
        WorkflowExecutor(nodes, edges, depth=4)


# ── 未知 workflow_manager → fallback simple（不炸）────────────────────────
async def test_unknown_manager_falls_back_to_simple(db_session):
    nodes, edges = _graph()
    wf = WorkflowExecutor(nodes, edges, workflow_manager="bogus")
    assert wf.workflow_manager == "simple"
    _events, answer = await _collect(wf, "urgent")
    assert answer == "URGENT"
