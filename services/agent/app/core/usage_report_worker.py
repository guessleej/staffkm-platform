"""Nightly job: aggregate yesterday's usage per workspace → Stripe meter API. v4.8 H.

對齊 v4.1 trial_expiry_worker pattern：safe_beat → 主邏輯 → log。
- 找 plan='usage' 且 status='active' 的 workspace
- 聚合 model_usage_logs 昨日 cost/tokens
- 透過 core.billing.report_usage_to_stripe 寫 usage_reports + call Stripe (placeholder)
"""
from __future__ import annotations
import asyncio
import datetime as dt

import structlog
from sqlalchemy import text

log = structlog.get_logger()


async def _aggregate_and_report(session_factory) -> int:
    """For each workspace with active 'usage' plan, sum yesterday's cost and call Stripe."""
    if not session_factory:
        return 0
    yesterday_start = (dt.datetime.utcnow() - dt.timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0,
    )
    yesterday_end = yesterday_start + dt.timedelta(days=1)

    async with session_factory() as session:
        r = await session.execute(text("""
            SELECT workspace_id FROM billing_accounts
            WHERE plan = 'usage' AND status = 'active'
        """))
        ws_ids = [str(row.workspace_id) for row in r.fetchall()]

    count = 0
    for ws_id in ws_ids:
        async with session_factory() as session:
            r = await session.execute(text("""
                SELECT
                    COALESCE(SUM(total_tokens), 0)::BIGINT AS tokens,
                    COALESCE(SUM(cost_usd), 0)::NUMERIC(12,6) AS cost
                FROM model_usage_logs
                WHERE workspace_id = :ws
                  AND created_at >= :s AND created_at < :e
            """), {"ws": ws_id, "s": yesterday_start, "e": yesterday_end})
            row = r.fetchone()
            tokens = int(row.tokens or 0)
            cost = float(row.cost or 0)

        if tokens > 0:
            async with session_factory() as session:
                from app.core.billing import report_usage_to_stripe
                await report_usage_to_stripe(
                    session, ws_id, yesterday_start, yesterday_end, tokens, cost,
                )
                count += 1

    log.info("usage_report_run", workspaces_reported=count)
    return count


async def usage_report_loop(session_factory_getter, interval_sec: int = 3600 * 6):
    """每 6 小時跑一次（idempotent，已 report 過跳過）。"""
    from app.core.heartbeat import safe_beat
    while True:
        await safe_beat(session_factory_getter, worker_name="usage_report_worker")
        try:
            sf = session_factory_getter()
            if sf is not None:
                await _aggregate_and_report(sf)
        except Exception as e:
            log.error("usage_report_loop_failed", error=str(e))
        await asyncio.sleep(interval_sec)
