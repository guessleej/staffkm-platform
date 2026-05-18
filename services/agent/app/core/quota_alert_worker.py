"""Quota alert worker — v3.3 D2

每 10 分鐘掃 quota usage，超 threshold 發通知。
每月一次：alert_id + month 進 quota_alert_fires，避免重發。
月初自然 reset（新 month、新 fire 紀錄）。

dispatch 失敗只 log，不重試（下回合會再來）。Email 暫只 log，未來接 SMTP。
"""
from __future__ import annotations

import asyncio
import datetime as dt

import httpx
import structlog
from sqlalchemy import text

log = structlog.get_logger()


async def _evaluate_and_fire(session) -> None:
    """掃所有 enabled alert，比對當月用量，超 threshold 且本月未發過就發。"""
    now = dt.datetime.utcnow()
    month_start = now.replace(day=1).date()

    # ── workspace-scope alerts ───────────────────────────────
    ws_rows = await session.execute(text("""
        SELECT a.id, a.workspace_id, a.scope, a.threshold_pct, a.channel, a.target,
               q.monthly_token_cap, q.monthly_cost_cap_usd,
               COALESCE((SELECT SUM(total_tokens) FROM model_usage_logs m
                         WHERE m.workspace_id = a.workspace_id
                           AND m.created_at >= date_trunc('month', now())
               ), 0)::BIGINT AS tokens_used,
               COALESCE((SELECT SUM(cost_usd) FROM model_usage_logs m
                         WHERE m.workspace_id = a.workspace_id
                           AND m.created_at >= date_trunc('month', now())
               ), 0)::NUMERIC AS cost_used
        FROM quota_alerts a
        LEFT JOIN workspace_quotas q ON q.workspace_id = a.workspace_id
        WHERE a.enabled = TRUE AND a.scope = 'workspace'
    """))
    for r in ws_rows.fetchall():
        d = dict(r._mapping)
        token_pct = (
            int(d["tokens_used"]) / int(d["monthly_token_cap"]) * 100
            if d.get("monthly_token_cap") else 0
        )
        cost_pct = (
            float(d["cost_used"]) / float(d["monthly_cost_cap_usd"]) * 100
            if d.get("monthly_cost_cap_usd") else 0
        )
        pct = max(token_pct, cost_pct)
        if pct < d["threshold_pct"]:
            continue
        chk = await session.execute(
            text("SELECT 1 FROM quota_alert_fires WHERE alert_id = :a AND month = :m"),
            {"a": str(d["id"]), "m": month_start},
        )
        if chk.fetchone():
            continue
        await _dispatch(session, d, pct, scope_label="workspace")
        await session.execute(
            text(
                "INSERT INTO quota_alert_fires (alert_id, month) "
                "VALUES (:a, :m) ON CONFLICT DO NOTHING"
            ),
            {"a": str(d["id"]), "m": month_start},
        )

    # ── user-scope alerts ────────────────────────────────────
    # 對每個 user-scope alert，掃這個 workspace 內所有有 user_quotas 設定的 user
    # 若任一 user 的用量比例超 threshold → 發一次（本月一次）
    user_rows = await session.execute(text("""
        SELECT a.id AS alert_id, a.workspace_id, a.threshold_pct, a.channel, a.target,
               uq.user_id, uq.monthly_token_cap, uq.monthly_cost_cap_usd,
               COALESCE((SELECT SUM(total_tokens) FROM model_usage_logs m
                         WHERE m.workspace_id = a.workspace_id
                           AND m.user_id = uq.user_id
                           AND m.created_at >= date_trunc('month', now())
               ), 0)::BIGINT AS tokens_used,
               COALESCE((SELECT SUM(cost_usd) FROM model_usage_logs m
                         WHERE m.workspace_id = a.workspace_id
                           AND m.user_id = uq.user_id
                           AND m.created_at >= date_trunc('month', now())
               ), 0)::NUMERIC AS cost_used
        FROM quota_alerts a
        JOIN user_quotas uq ON uq.workspace_id = a.workspace_id
        WHERE a.enabled = TRUE AND a.scope = 'user'
    """))
    # 每個 alert 本月只發一次（取首位達 threshold 的 user）
    fired_in_run: set[str] = set()
    for r in user_rows.fetchall():
        d = dict(r._mapping)
        alert_id = str(d["alert_id"])
        if alert_id in fired_in_run:
            continue
        token_pct = (
            int(d["tokens_used"]) / int(d["monthly_token_cap"]) * 100
            if d.get("monthly_token_cap") else 0
        )
        cost_pct = (
            float(d["cost_used"]) / float(d["monthly_cost_cap_usd"]) * 100
            if d.get("monthly_cost_cap_usd") else 0
        )
        pct = max(token_pct, cost_pct)
        if pct < d["threshold_pct"]:
            continue
        chk = await session.execute(
            text("SELECT 1 FROM quota_alert_fires WHERE alert_id = :a AND month = :m"),
            {"a": alert_id, "m": month_start},
        )
        if chk.fetchone():
            fired_in_run.add(alert_id)
            continue
        await _dispatch(
            session,
            {**d, "id": d["alert_id"], "user_id": d["user_id"]},
            pct,
            scope_label="user",
        )
        await session.execute(
            text(
                "INSERT INTO quota_alert_fires (alert_id, month) "
                "VALUES (:a, :m) ON CONFLICT DO NOTHING"
            ),
            {"a": alert_id, "m": month_start},
        )
        fired_in_run.add(alert_id)

    await session.commit()


async def _dispatch(session, alert: dict, pct: float, *, scope_label: str = "workspace") -> None:
    """依 channel 發通知。webhook/slack 走 outbox 重試；email 維持直送 SMTP。"""
    who = f"user {alert.get('user_id')}" if scope_label == "user" else f"workspace {alert.get('workspace_id')}"
    msg = f"[staffKM] {scope_label} 用量 {pct:.0f}% (threshold {alert['threshold_pct']}%) — {who}"
    try:
        if alert["channel"] == "webhook":
            from app.core.webhook_outbox import enqueue_webhook
            await enqueue_webhook(
                session,
                url=alert["target"],
                body={
                    "text": msg,
                    "alert_id": str(alert["id"]),
                    "scope": scope_label,
                    "pct": pct,
                },
                workspace_id=alert.get("workspace_id"),
                source_type="quota_alert",
                source_id=alert["id"],
            )
            await session.commit()
        elif alert["channel"] == "slack":
            from app.core.webhook_outbox import enqueue_webhook
            await enqueue_webhook(
                session,
                url=alert["target"],
                body={"text": msg},
                workspace_id=alert.get("workspace_id"),
                source_type="quota_alert",
                source_id=alert["id"],
            )
            await session.commit()
        elif alert["channel"] == "email":
            # v3.4 P2: 真接 SMTP（SMTP_HOST 未設則 send_email 內部 log skip）
            from app.core.email import send_email
            await send_email(
                to=alert["target"],
                subject=f"[staffKM] 配額告警 {pct:.0f}% ({scope_label})",
                body=msg,
            )
    except Exception as e:
        log.warning("quota_alert_dispatch_failed", channel=alert["channel"], error=str(e))


async def alert_worker_loop(session_factory_getter, interval_sec: int = 600) -> None:
    """背景常駐：每 interval_sec 跑一次 evaluate。"""
    from app.core.heartbeat import safe_beat
    while True:
        await safe_beat(session_factory_getter, worker_name="quota_alert_worker")
        try:
            sf = session_factory_getter()
            if sf is not None:
                async with sf() as session:
                    await _evaluate_and_fire(session)
        except Exception as e:
            log.error("quota_alert_loop_failed", error=str(e))
        await asyncio.sleep(interval_sec)
