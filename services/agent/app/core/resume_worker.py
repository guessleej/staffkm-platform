"""Workflow resume worker — v3.5 P2。

每 30 秒掃：
1. workflow_approvals.status IN ('approved','rejected') 且對應 event_trigger_runs.status='paused'
2. rejected → run.status='rejected'、finished_at=now()
3. approved → 載 application 的 workflow，從 paused 的 resume_node 之後續跑

簡化說明（v3.5）：
- 不重組 trigger 原始 input；user_input='' 開續跑（後續 PR 可從 workflow_run_steps 取）
- approved 直接跳過該 human_approval node，視為「通過」繼續執行
- multi-approver / timeout auto-reject 留 v3.6
"""
from __future__ import annotations
import asyncio

import structlog
from sqlalchemy import text

log = structlog.get_logger()


async def _find_resumable(session) -> list[dict]:
    """找已 approved/rejected 但對應 run 還是 paused 且尚未 resume 的 case。"""
    rows = await session.execute(text("""
        SELECT r.id            AS run_id,
               r.workspace_id  AS workspace_id,
               r.trigger_id    AS trigger_id,
               r.resume_node   AS resume_node,
               t.application_id AS application_id,
               t.input_template AS input_template,
               t.name           AS trigger_name,
               a.id             AS approval_id,
               a.status         AS approval_status
        FROM event_trigger_runs r
        JOIN event_triggers t      ON t.id = r.trigger_id
        JOIN workflow_approvals a  ON a.run_id = r.id
        WHERE r.status = 'paused'
          AND a.status IN ('approved', 'rejected')
          AND r.resumed_at IS NULL
        ORDER BY a.resolved_at ASC
        LIMIT 5
    """))
    return [dict(r._mapping) for r in rows.fetchall()]


async def _resume_or_reject(session_factory, rec: dict) -> None:
    """處理單筆。新開 session，避免長 transaction。"""
    run_id = str(rec["run_id"])

    # ── rejected 路徑 ─────────────────────────────────────────────
    if rec["approval_status"] == "rejected":
        async with session_factory() as session:
            try:
                await session.execute(text("""
                    UPDATE event_trigger_runs
                    SET status='rejected', resumed_at=now(), finished_at=now()
                    WHERE id=:id
                """), {"id": run_id})
                await session.execute(text("""
                    UPDATE event_triggers SET last_status='rejected' WHERE id=:id
                """), {"id": str(rec["trigger_id"])})
                await session.commit()
                log.info("workflow_run_rejected", run=run_id)
            except Exception as e:
                log.error("resume_reject_failed", run=run_id, error=str(e))
        return

    # ── approved 路徑：重新跑 workflow，從 resume_node 之後 ──────
    try:
        from app.core.workflow.executor import WorkflowExecutor, WorkflowPaused
        from app.core.trigger_dispatcher import _load_workflow

        async with session_factory() as session:
            nodes, edges, mgr, created_by = await _load_workflow(
                session, rec["application_id"], rec["workspace_id"]
            )

        if not nodes:
            async with session_factory() as session:
                await session.execute(text("""
                    UPDATE event_trigger_runs
                    SET status='error', resumed_at=now(), finished_at=now(),
                        output_summary = COALESCE(output_summary,'') || E'\n[resume] workflow 尚無節點'
                    WHERE id=:id
                """), {"id": run_id})
                await session.commit()
            log.warning("resume_no_nodes", run=run_id)
            return

        executor = WorkflowExecutor(
            nodes=nodes,
            edges=edges,
            workspace_id=str(rec["workspace_id"]),
            user_id=created_by or "resume-worker",
            roles=["editor"],
            workflow_manager=mgr or "simple",
            application_id=str(rec["application_id"]),
            run_id=rec["run_id"],
            resume_from_node=rec["resume_node"],
        )

        events: list[str] = []
        final_status = "ok"
        try:
            async for ev in executor.execute(user_input="", user_id=created_by or "resume-worker"):
                name = ev.get("event", "")
                events.append(name)
                if name == "error":
                    final_status = "error"
        except WorkflowPaused as e:
            # 又 hit 另一個 human_approval node（多階核 — v3.5 簡化視為仍 paused）
            log.info("resume_hit_another_pause", run=run_id, node=e.node_key)
            return

        async with session_factory() as session:
            await session.execute(text("""
                UPDATE event_trigger_runs
                SET status = :s, resumed_at = now(), finished_at = now(),
                    output_summary = COALESCE(output_summary,'') || E'\n[resumed] ' || :summary
                WHERE id=:id
            """), {
                "s": final_status,
                "summary": ",".join(events)[:1000],
                "id": run_id,
            })
            await session.execute(text("""
                UPDATE event_triggers SET last_status=:s WHERE id=:id
            """), {"s": final_status, "id": str(rec["trigger_id"])})
            await session.commit()
        log.info("workflow_run_resumed", run=run_id, status=final_status)
    except Exception as e:
        log.error("resume_failed", run=run_id, error=str(e))
        try:
            async with session_factory() as session:
                await session.execute(text("""
                    UPDATE event_trigger_runs
                    SET status='error', resumed_at=now(), finished_at=now(),
                        output_summary = COALESCE(output_summary,'') || E'\n[resume_failed] ' || :err
                    WHERE id=:id
                """), {"err": str(e)[:500], "id": run_id})
                await session.commit()
        except Exception:
            pass


async def resume_worker_loop(session_factory_getter, interval_sec: int = 30) -> None:
    """背景循環：每 interval_sec 秒掃 approved/rejected approvals 並 resume / reject 對應 run。"""
    log.info("resume_worker_started", interval_sec=interval_sec)
    while True:
        try:
            sf = session_factory_getter()
            if sf is not None:
                async with sf() as session:
                    todos = await _find_resumable(session)
                for rec in todos:
                    await _resume_or_reject(sf, rec)
        except asyncio.CancelledError:
            log.info("resume_worker_cancelled")
            raise
        except Exception as e:
            log.warning("resume_loop_failed", error=str(e))
        await asyncio.sleep(interval_sec)
