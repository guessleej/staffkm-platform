"""workflow human_approval / resume 狀態機整合測試（真 PostgreSQL）。

守的是 pause→approve/reject→resume 的持久化骨幹（走錯 = 卡單或誤放行）：
- **pause**：executor 跑到 human_approval 節點 → 寫 workflow_approvals(pending) +
  raise WorkflowPaused + 記一筆 paused step（不真執行下游）。
- **claim**：resume_worker `_find_resumable` 只挑「paused run + approved/rejected approval +
  尚未 resume」；pending approval / 已 resume 的不挑（避免重複 resume / 提早 resume）。
- **reject**：`_resume_or_reject` rejected 路徑 → run.status='rejected' + resumed_at/finished_at。

approved 路徑會重跑 executor（需載 application workflow，重）→ 不在本檔；本檔釘住 DB
狀態機的選取/落地正確性（最易因 race / SQL 寫錯而誤放行或卡單）。
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.core.resume_worker import _find_resumable, _resume_or_reject
from app.core.workflow.executor import WorkflowExecutor, WorkflowPaused
from staffkm_core.utils import database as _db

pytestmark = pytest.mark.asyncio


def _ws() -> str:
    return str(uuid.uuid4())


async def _seed_paused_run(session, ws, *, approval_status=None, resumed=False,
                           resume_node="appr") -> dict:
    """建 trigger + paused run（可選帶一筆 approval）。回 {run_id, trigger_id, approval_id}。"""
    trigger_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    await session.execute(text(
        "INSERT INTO event_triggers (id, workspace_id, application_id, name, kind) "
        "VALUES (CAST(:t AS uuid), CAST(:ws AS uuid), CAST(:app AS uuid), 'trg', 'manual')"),
        {"t": trigger_id, "ws": ws, "app": str(uuid.uuid4())})
    await session.execute(text(
        "INSERT INTO event_trigger_runs (id, trigger_id, workspace_id, status, resume_node, "
        "                                paused_at, resumed_at) "
        "VALUES (CAST(:r AS uuid), CAST(:t AS uuid), CAST(:ws AS uuid), 'paused', :rn, now(), "
        "        CASE WHEN :res THEN now() ELSE NULL END)"),
        {"r": run_id, "t": trigger_id, "ws": ws, "rn": resume_node, "res": resumed})
    approval_id = None
    if approval_status is not None:
        approval_id = str(uuid.uuid4())
        await session.execute(text(
            "INSERT INTO workflow_approvals (id, run_id, workspace_id, node_key, status, resolved_at) "
            "VALUES (CAST(:a AS uuid), CAST(:r AS uuid), CAST(:ws AS uuid), :nk, :st, now())"),
            {"a": approval_id, "r": run_id, "ws": ws, "nk": resume_node, "st": approval_status})
    await session.commit()
    return {"run_id": run_id, "trigger_id": trigger_id, "approval_id": approval_id}


# ── PAUSE：human_approval 節點 → pending approval + WorkflowPaused + paused step ──
async def test_human_approval_pauses_and_persists_pending(db_session):
    run_id = uuid.uuid4()
    ws = _ws()
    nodes = [
        {"node_key": "start", "node_type": "start", "config": {}},
        {"node_key": "appr", "node_type": "human_approval",
         "config": {"payload_template": "請主管核准 {{user_input}}"}},
    ]
    edges = [{"source_node_key": "start", "target_node_key": "appr"}]
    wf = WorkflowExecutor(nodes, edges, run_id=run_id, workspace_id=ws)

    with pytest.raises(WorkflowPaused):
        [ev async for ev in wf.execute("報帳單 #42")]

    # 寫了一筆 pending approval（run_id + node_key）
    appr = (await db_session.execute(text(
        "SELECT status, node_key FROM workflow_approvals WHERE run_id = CAST(:r AS uuid)"),
        {"r": str(run_id)})).mappings().all()
    assert len(appr) == 1
    assert appr[0]["status"] == "pending" and appr[0]["node_key"] == "appr"

    # 記了一筆 paused step
    paused = (await db_session.execute(text(
        "SELECT count(*) FROM workflow_run_steps WHERE run_id = CAST(:r AS uuid) AND status='paused'"),
        {"r": str(run_id)})).scalar()
    assert paused == 1


# ── CLAIM：_find_resumable 的選取規則 ─────────────────────────────────────
async def test_find_resumable_picks_paused_approved(db_session):
    ws = _ws()
    seeded = await _seed_paused_run(db_session, ws, approval_status="approved")
    rows = await _find_resumable(db_session)
    assert any(str(r["run_id"]) == seeded["run_id"] for r in rows)


async def test_find_resumable_skips_pending_approval(db_session):
    ws = _ws()
    seeded = await _seed_paused_run(db_session, ws, approval_status="pending")
    rows = await _find_resumable(db_session)
    assert all(str(r["run_id"]) != seeded["run_id"] for r in rows)  # pending 不該被挑


async def test_find_resumable_skips_already_resumed(db_session):
    ws = _ws()
    seeded = await _seed_paused_run(db_session, ws, approval_status="approved", resumed=True)
    rows = await _find_resumable(db_session)
    assert all(str(r["run_id"]) != seeded["run_id"] for r in rows)  # resumed_at 已設 → 不重複 resume


# ── REJECT：_resume_or_reject 把 run 標 rejected + 收尾時間 ────────────────
async def test_resume_or_reject_rejected_path(db_session):
    ws = _ws()
    await _seed_paused_run(db_session, ws, approval_status="rejected")
    rec = next(r for r in await _find_resumable(db_session))

    await _resume_or_reject(_db._session_factory, rec)

    row = (await db_session.execute(text(
        "SELECT status, resumed_at, finished_at FROM event_trigger_runs WHERE id = CAST(:r AS uuid)"),
        {"r": str(rec["run_id"])})).mappings().one()
    assert row["status"] == "rejected"
    assert row["resumed_at"] is not None and row["finished_at"] is not None
