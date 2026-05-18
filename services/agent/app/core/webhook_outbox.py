"""Webhook outbox pattern — v3.6 P1。

enqueue_webhook() — caller 不直接呼叫 httpx，而是 insert outbox row。
webhook_dispatcher_loop — 背景 loop，claim pending row → POST → 成功 mark delivered / 失敗 schedule next retry。

Backoff schedule (秒): 60, 300, 1800, 7200, 43200  (1m, 5m, 30m, 2h, 12h)
5 次後 status='failed' (DLQ)。
"""
from __future__ import annotations
import asyncio
import datetime as dt
import json as _json
import uuid
from typing import Any

import httpx
import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger()

BACKOFF_SECONDS = [60, 300, 1800, 7200, 43200]
MAX_ATTEMPTS = len(BACKOFF_SECONDS)


async def enqueue_webhook(
    session: AsyncSession,
    *,
    url: str,
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    method: str = "POST",
    workspace_id: str | uuid.UUID | None = None,
    source_type: str | None = None,
    source_id: str | uuid.UUID | None = None,
) -> str:
    """寫一筆 pending outbox row、回 outbox.id。caller 負責 commit。"""
    r = await session.execute(text("""
        INSERT INTO webhook_outbox (
            workspace_id, url, method, headers, body, source_type, source_id
        ) VALUES (
            :ws, :url, :method, CAST(:hdr AS jsonb), CAST(:body AS jsonb),
            :stype, :sid
        )
        RETURNING id
    """), {
        "ws": str(workspace_id) if workspace_id else None,
        "url": url,
        "method": method.upper(),
        "hdr": _json.dumps(headers or {}, ensure_ascii=False),
        "body": _json.dumps(body or {}, ensure_ascii=False, default=str),
        "stype": source_type,
        "sid": str(source_id) if source_id else None,
    })
    return str(r.scalar_one())


async def _claim_one(session: AsyncSession) -> dict | None:
    """取一筆 pending + due 的 row，標 in_flight。"""
    rows = await session.execute(text("""
        SELECT id, url, method, headers, body, attempts
        FROM webhook_outbox
        WHERE status = 'pending' AND next_retry_at <= now()
        ORDER BY next_retry_at ASC
        LIMIT 1
        FOR UPDATE SKIP LOCKED
    """))
    row = rows.fetchone()
    if not row:
        return None
    d = dict(row._mapping)
    await session.execute(
        text("UPDATE webhook_outbox SET status='in_flight' WHERE id = :id"),
        {"id": str(d["id"])},
    )
    await session.commit()
    return d


async def _mark_delivered(session: AsyncSession, oid: str, status_code: int) -> None:
    await session.execute(text("""
        UPDATE webhook_outbox
        SET status='delivered', delivered_at=now(),
            last_status_code=:sc, attempts=attempts+1
        WHERE id=:id
    """), {"id": oid, "sc": status_code})
    await session.commit()


async def _mark_retry_or_fail(
    session: AsyncSession, oid: str, attempts: int, error: str, sc: int | None
) -> None:
    next_attempt = attempts + 1
    if next_attempt >= MAX_ATTEMPTS:
        await session.execute(text("""
            UPDATE webhook_outbox
            SET status='failed', attempts=:att,
                last_error=:err, last_status_code=:sc
            WHERE id=:id
        """), {"id": oid, "att": next_attempt, "err": error[:1000], "sc": sc})
        log.warning("webhook_outbox_dlq", id=oid, attempts=next_attempt)
    else:
        backoff = BACKOFF_SECONDS[next_attempt - 1]  # 0-indexed
        next_retry = dt.datetime.utcnow() + dt.timedelta(seconds=backoff)
        await session.execute(text("""
            UPDATE webhook_outbox
            SET status='pending', attempts=:att,
                last_error=:err, last_status_code=:sc,
                next_retry_at=:nra
            WHERE id=:id
        """), {
            "id": oid, "att": next_attempt,
            "err": error[:1000], "sc": sc,
            "nra": next_retry,
        })
        log.info("webhook_outbox_scheduled", id=oid, attempt=next_attempt, backoff_sec=backoff)
    await session.commit()


async def _deliver(session_factory) -> bool:
    """跑一筆。回 True 代表處理過任何工作。"""
    async with session_factory() as session:
        rec = await _claim_one(session)
    if not rec:
        return False
    oid = str(rec["id"])
    attempts = int(rec["attempts"])
    body = rec["body"] or {}
    headers = rec["headers"] or {}
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.request(rec["method"], rec["url"], json=body, headers=headers)
            if 200 <= r.status_code < 300:
                async with session_factory() as session:
                    await _mark_delivered(session, oid, r.status_code)
                return True
            err = f"HTTP {r.status_code}: {r.text[:200]}"
            async with session_factory() as session:
                await _mark_retry_or_fail(session, oid, attempts, err, r.status_code)
    except Exception as e:
        async with session_factory() as session:
            await _mark_retry_or_fail(session, oid, attempts, str(e), None)
    return True


async def webhook_dispatcher_loop(session_factory_getter, interval_sec: int = 30) -> None:
    """背景常駐：每 interval_sec 跑一輪、把所有 due rows 都處理掉。"""
    from app.core.heartbeat import safe_beat
    while True:
        await safe_beat(session_factory_getter, worker_name="webhook_dispatcher")
        try:
            sf = session_factory_getter()
            if sf is not None:
                processed = 0
                while await _deliver(sf):
                    processed += 1
                    if processed >= 50:  # 一輪上限避免餓死其他 task
                        break
        except Exception as e:
            log.error("webhook_dispatcher_loop_failed", error=str(e))
        await asyncio.sleep(interval_sec)
