"""Trigger Dispatcher（v2.1 12-4）。

從 event_trigger_runs(status='queued') 取出一筆，背景跑 workflow，然後寫回結果。

設計：
- 每 10s 掃一次（比 worker 60s 更頻繁；確保 fire 後快速進入執行）
- 一次只處理一筆，避免長 workflow 互相干擾；多副本由 FOR UPDATE SKIP LOCKED 保護
- 執行流程：
  1. SELECT run + 對應 trigger 一筆（status='queued' AND 同 workspace）
  2. UPDATE run SET status='running', finished_at=NULL（claim）
  3. 載入 application 對應 workflow_nodes / workflow_edges
  4. WorkflowExecutor.execute(user_input=trigger.input_template) 跑完
  5. 收集所有 SSE event 串成 output_summary（最多 4KB）
  6. UPDATE run SET status='ok'|'error' + output_summary + finished_at

多副本安全：使用 SELECT ... FOR UPDATE SKIP LOCKED 確保同一筆 run 不被兩個 dispatcher 拿走。
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any

import structlog
from sqlalchemy import text

from app.core.workflow.executor import WorkflowExecutor

log = structlog.get_logger()


async def _claim_one(session) -> dict[str, Any] | None:
    """以 FOR UPDATE SKIP LOCKED 撈一筆 queued run 並標 running；找不到回 None。"""
    rows = await session.execute(
        text(
            """
            SELECT
                r.id              AS run_id,
                r.trigger_id      AS trigger_id,
                r.workspace_id    AS workspace_id,
                t.application_id  AS application_id,
                t.input_template  AS input_template,
                t.name            AS trigger_name
            FROM event_trigger_runs r
            JOIN event_triggers t ON t.id = r.trigger_id
            WHERE r.status = 'queued'
            ORDER BY r.fired_at ASC
            LIMIT 1
            FOR UPDATE OF r SKIP LOCKED
            """
        )
    )
    row = rows.fetchone()
    if not row:
        return None
    rec = dict(row._mapping)
    await session.execute(
        text("UPDATE event_trigger_runs SET status = 'running' WHERE id = :id"),
        {"id": str(rec["run_id"])},
    )
    await session.commit()
    return rec


async def _load_workflow(session, app_id, workspace_id) -> tuple[list, list, str]:
    nodes_rows = await session.execute(
        text(
            "SELECT * FROM workflow_nodes "
            "WHERE application_id = :app_id AND workspace_id = :ws "
            "ORDER BY created_at"
        ),
        {"app_id": str(app_id), "ws": str(workspace_id)},
    )
    edges_rows = await session.execute(
        text(
            "SELECT * FROM workflow_edges "
            "WHERE application_id = :app_id AND workspace_id = :ws"
        ),
        {"app_id": str(app_id), "ws": str(workspace_id)},
    )
    nodes: list = [dict(r._mapping) for r in nodes_rows.fetchall()]
    edges: list = [dict(r._mapping) for r in edges_rows.fetchall()]
    for n in nodes:
        if isinstance(n.get("config"), str):
            n["config"] = json.loads(n["config"])

    mgr_row = await session.execute(
        text("SELECT workflow_manager, created_by FROM applications WHERE id = :id"),
        {"id": str(app_id)},
    )
    mgr_row_data = mgr_row.fetchone()
    workflow_manager = (
        dict(mgr_row_data._mapping).get("workflow_manager") if mgr_row_data else None
    ) or "simple"
    created_by = (
        str(dict(mgr_row_data._mapping).get("created_by")) if mgr_row_data else ""
    )
    return nodes, edges, workflow_manager, created_by  # type: ignore[return-value]


async def _run_workflow(rec: dict[str, Any], session) -> tuple[str, str]:
    """跑 workflow；回 (status, output_summary)。"""
    app_id      = rec["application_id"]
    workspace   = rec["workspace_id"]
    user_input  = rec.get("input_template") or ""

    try:
        nodes, edges, mgr, created_by = await _load_workflow(session, app_id, workspace)
    except Exception as e:
        return "error", f"load_workflow_failed: {e}"

    if not nodes:
        return "error", "workflow 尚無節點"

    # 用 application 的 created_by 充當 audit user（trigger 不掛在某個真人 session）
    executor = WorkflowExecutor(
        nodes=nodes,
        edges=edges,
        workspace_id=str(workspace),
        user_id=created_by or "trigger-dispatcher",
        roles=["editor"],   # trigger 跑時以 editor 角色執行（最小寫入權）
        workflow_manager=mgr,
        application_id=str(app_id),  # v3.3：metering 歸帳
    )

    events: list[str] = []
    final_status = "ok"
    try:
        async for ev in executor.execute(user_input=user_input, user_id=created_by or "trigger-dispatcher"):
            name = ev.get("event", "")
            data = ev.get("data", "")
            if isinstance(data, str) and len(data) > 200:
                data = data[:200] + "…"
            events.append(f"{name}:{data}")
            if name == "error":
                final_status = "error"
    except Exception as e:
        # v3.3：quota 超額 → 標 quota_exceeded（free-text status，schema 是 VARCHAR(16)）
        from app.core.usage import QuotaExceeded
        if isinstance(e, QuotaExceeded):
            return "quota_exceeded", f"quota_exceeded: {e}"
        return "error", f"executor_raised: {e}"

    summary = "\n".join(events)[:4000]
    return final_status, summary


async def _process_one(session_factory) -> bool:
    """處理一筆 queued run；回 True 代表處理過任何工作。"""
    if session_factory is None:
        return False
    async with session_factory() as session:
        rec = await _claim_one(session)
        if not rec:
            return False
    # 在新 session 跑 workflow，避免長交易卡 lock
    async with session_factory() as session:
        try:
            status, summary = await _run_workflow(rec, session)
        except Exception as e:
            status, summary = "error", f"dispatcher_raised: {e}"
        try:
            await session.execute(
                text(
                    "UPDATE event_trigger_runs "
                    "SET status = :s, output_summary = :o, finished_at = :ts "
                    "WHERE id = :id"
                ),
                {
                    "s":  status,
                    "o":  summary,
                    "ts": datetime.utcnow(),
                    "id": str(rec["run_id"]),
                },
            )
            await session.execute(
                text(
                    "UPDATE event_triggers SET last_status = :s, last_error = :err "
                    "WHERE id = :id"
                ),
                {
                    "s":   status,
                    "err": (summary if status == "error" else None),
                    "id":  str(rec["trigger_id"]),
                },
            )
            await session.commit()
        except Exception as e:
            log.warning("dispatcher_writeback_failed", run=str(rec["run_id"]), error=str(e))
    log.info("dispatcher_run_done", run=str(rec["run_id"]),
             trigger=str(rec["trigger_id"]), status=status)
    return True


async def trigger_dispatcher_loop(session_factory_getter, *, interval_sec: int = 10) -> None:
    """背景循環：每 interval_sec 秒嘗試處理一筆 queued run。

    若處理到一筆 → 立刻再嘗試下一筆（背壓友善）；都沒有才 sleep。
    """
    log.info("trigger_dispatcher_started", interval_sec=interval_sec)
    while True:
        try:
            did = await _process_one(session_factory_getter())
            if did:
                continue
        except asyncio.CancelledError:
            log.info("trigger_dispatcher_cancelled")
            raise
        except Exception as e:
            log.warning("dispatcher_iteration_failed", error=str(e))
        await asyncio.sleep(interval_sec)
