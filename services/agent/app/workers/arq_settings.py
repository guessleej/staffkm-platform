"""Arq WorkerSettings — v4.0 P3 / P4。

跟 agent service 共用 codebase；用 docker compose 起獨立 process:
    command: python -m arq app.workers.arq_settings.WorkerSettings

把 v3.6 五個 in-process worker loop 對應拆成 5 個 arq job（cron schedule
對應原 interval_sec），由獨立 worker container 跑 → agent service 可水平
scale 而不重複觸發。

注意：兩個 backend（inprocess / arq）不能同時跑（會 race 對同一張表 claim
queued runs / approvals / webhooks）。請用 env `WORKER_BACKEND` 切換。
"""
from __future__ import annotations

import structlog
from arq import cron

from app.config import settings as app_settings
from staffkm_core.utils import database as _db
from staffkm_core.utils.arq_settings import REDIS_SETTINGS
from staffkm_core.utils.database import init_db

log = structlog.get_logger()


# ── Lifecycle hooks ──────────────────────────────────────────────────

async def startup(ctx):
    """Arq worker startup — init DB pool 給 jobs 用。"""
    init_db(app_settings.DB_URL)
    log.info("arq_worker_started")


async def shutdown(ctx):
    log.info("arq_worker_stopping")


# ── Job functions（每個只跑「一輪要做的事」，cron 控制節奏）─────────

async def trigger_scan_job(ctx) -> None:
    """掃 due triggers → 寫 queued runs。對應原 trigger_worker_loop 一輪。"""
    from app.core.trigger_worker import _scan_due_triggers
    if _db._session_factory is None:
        return
    async with _db._session_factory() as session:
        await _scan_due_triggers(session)


async def trigger_dispatch_job(ctx) -> None:
    """處理 N 筆 queued runs（一輪 best-effort，最多 5 筆）。"""
    from app.core.trigger_dispatcher import _process_one
    if _db._session_factory is None:
        return
    for _ in range(5):
        if not await _process_one(_db._session_factory):
            break


async def resume_check_job(ctx) -> None:
    """掃 approved/rejected paused runs → resume / mark rejected。"""
    from app.core.resume_worker import _find_resumable, _resume_or_reject
    if _db._session_factory is None:
        return
    async with _db._session_factory() as session:
        recs = await _find_resumable(session)
    for rec in recs:
        await _resume_or_reject(_db._session_factory, rec)


async def quota_alert_job(ctx) -> None:
    """evaluate quota → enqueue webhook outbox / send email。"""
    from app.core.quota_alert_worker import _evaluate_and_fire
    if _db._session_factory is None:
        return
    async with _db._session_factory() as session:
        await _evaluate_and_fire(session)


async def trial_expiry_job(ctx) -> None:
    """v4.1 A：凍結過期 trial workspace。對應 trial_expiry_loop 一輪。"""
    from app.core.trial_expiry_worker import _freeze_expired
    if _db._session_factory is None:
        return
    async with _db._session_factory() as session:
        n = await _freeze_expired(session)
        if n > 0:
            log.info("trial_frozen", count=n)


async def webhook_dispatch_job(ctx) -> None:
    """處理 pending webhook outbox rows（一輪最多 50 筆）。"""
    from app.core.webhook_outbox import _deliver
    if _db._session_factory is None:
        return
    processed = 0
    while await _deliver(_db._session_factory):
        processed += 1
        if processed >= 50:
            break


# ── WorkerSettings ───────────────────────────────────────────────────

class WorkerSettings:
    """Arq worker config — 啟動：python -m arq app.workers.arq_settings.WorkerSettings"""

    functions = [
        trigger_scan_job,
        trigger_dispatch_job,
        resume_check_job,
        quota_alert_job,
        webhook_dispatch_job,
        trial_expiry_job,
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = REDIS_SETTINGS

    # cron schedule（替代 v3.6 in-process loop interval_sec）
    cron_jobs = [
        cron(trigger_scan_job,     minute=set(range(0, 60))),        # 每分鐘 (~60s)
        cron(trigger_dispatch_job, second={0, 10, 20, 30, 40, 50}),  # 每 10s
        cron(resume_check_job,     second={0, 30}),                  # 每 30s
        cron(quota_alert_job,      minute={0, 10, 20, 30, 40, 50}),  # 每 10 分鐘
        cron(webhook_dispatch_job, second={0, 30}),                  # 每 30s
        cron(trial_expiry_job,     minute={0}),                      # 每小時 (v4.1 A)
    ]
