"""Event Trigger Worker（M4 啟動）。

每 60 秒掃一次 event_triggers，將 next_fire_at <= now 的 triggers 標記為已觸發
並插入一筆 event_trigger_runs（status='queued'）。

真實「執行 workflow」的部分留給 M4 中段 — 目前 worker 只負責：
1) 計算下一次 next_fire_at（基於 interval_sec 或 cron）
2) 標記 last_fired_at
3) 寫一筆 queued run；外部 executor 從 queue 拿出來執行

croniter 套件為 optional：未安裝時 cron 觸發會 noop 並 log warning。
這樣不引入硬依賴；M4 中段如需 cron 再加 deps。
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta

import structlog
from sqlalchemy import text

log = structlog.get_logger()


def _try_croniter():
    try:
        from croniter import croniter  # type: ignore
        return croniter
    except ImportError:
        return None


def _next_fire(kind: str, *, interval_sec: int | None, cron_expr: str | None, now: datetime) -> datetime | None:
    if kind == "interval" and interval_sec and interval_sec > 0:
        return now + timedelta(seconds=interval_sec)
    if kind == "cron" and cron_expr:
        c = _try_croniter()
        if c is None:
            log.warning("trigger_cron_skipped_no_croniter", expr=cron_expr)
            return None
        try:
            return c(cron_expr, now).get_next(datetime)
        except Exception as e:
            log.warning("trigger_cron_parse_failed", expr=cron_expr, error=str(e))
            return None
    return None


async def _scan_and_fire(session_factory) -> None:
    if session_factory is None:
        return
    now = datetime.utcnow()
    async with session_factory() as session:
        # 取出 due triggers
        rows = await session.execute(
            text(
                """
                SELECT id, workspace_id, application_id, kind, cron_expr, interval_sec
                FROM event_triggers
                WHERE enabled = TRUE
                  AND (next_fire_at IS NOT NULL AND next_fire_at <= :now)
                LIMIT 100
                """
            ),
            {"now": now},
        )
        due = [dict(r._mapping) for r in rows.fetchall()]
        if not due:
            return

        log.info("trigger_due", count=len(due))

        for t in due:
            run_id = str(uuid.uuid4())
            nfa = _next_fire(
                t["kind"],
                interval_sec=t.get("interval_sec"),
                cron_expr=t.get("cron_expr"),
                now=now,
            )
            try:
                # 寫 queued run
                await session.execute(
                    text(
                        """
                        INSERT INTO event_trigger_runs (id, trigger_id, workspace_id, status)
                        VALUES (:id, :tid, :ws, 'queued')
                        """
                    ),
                    {"id": run_id, "tid": str(t["id"]), "ws": str(t["workspace_id"])},
                )
                # 更新 trigger 狀態
                await session.execute(
                    text(
                        """
                        UPDATE event_triggers
                        SET last_fired_at = :now,
                            next_fire_at  = :nfa,
                            last_status   = 'queued',
                            last_error    = NULL,
                            updated_at    = :now
                        WHERE id = :id
                        """
                    ),
                    {"now": now, "nfa": nfa, "id": str(t["id"])},
                )
            except Exception as e:
                log.warning("trigger_fire_failed", trigger=str(t["id"]), error=str(e))
        await session.commit()


async def trigger_worker_loop(session_factory_getter, *, interval_sec: int = 60) -> None:
    """背景循環：每 interval_sec 秒掃一次。

    session_factory_getter: 呼叫時取得目前的 session_factory（避免在 import 時鎖死）
    """
    from app.core.heartbeat import safe_beat
    log.info("trigger_worker_started", interval_sec=interval_sec)
    while True:
        await safe_beat(session_factory_getter, worker_name="trigger_worker")
        try:
            await _scan_and_fire(session_factory_getter())
        except asyncio.CancelledError:
            log.info("trigger_worker_cancelled")
            raise
        except Exception as e:
            log.warning("trigger_worker_iteration_failed", error=str(e))
        await asyncio.sleep(interval_sec)
