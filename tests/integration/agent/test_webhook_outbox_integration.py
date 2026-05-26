"""Webhook outbox 至少一次投遞狀態機整合測試（真 PostgreSQL）。

守的是 resilience 核心：webhook 不直接打 httpx，而是 outbox row → 背景 loop claim →
投遞 → 成功 delivered / 失敗指數退避重排 / 5 次進 DLQ(failed)。本檔測**狀態機本身**
（不碰 httpx）：enqueue / claim（FOR UPDATE SKIP LOCKED）/ mark_delivered /
mark_retry（退避排程）/ DLQ / due-gating。

production hardness：投遞語意走錯 = 通知漏發或狂發。純邏輯單元測不到 next_retry_at
的時間 gating 與 jsonb bind，要真 SQL round-trip。
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.core.webhook_outbox import (
    BACKOFF_SECONDS,
    MAX_ATTEMPTS,
    _claim_one,
    _mark_delivered,
    _mark_retry_or_fail,
    enqueue_webhook,
)

pytestmark = pytest.mark.asyncio


async def _row(session, oid):
    r = await session.execute(text(
        "SELECT status, attempts, last_status_code, last_error, delivered_at, "
        "       next_retry_at, (next_retry_at > now()) AS in_future "
        "FROM webhook_outbox WHERE id = CAST(:id AS uuid)"
    ), {"id": oid})
    return dict(r.mappings().one())


# ── enqueue ──────────────────────────────────────────────────────────────
async def test_enqueue_creates_pending_row(db_session):
    oid = await enqueue_webhook(db_session, url="https://hook.example/x",
                                body={"event": "ping"}, headers={"X-Test": "1"},
                                source_type="trigger", source_id=uuid.uuid4())
    await db_session.commit()
    row = await _row(db_session, oid)
    assert row["status"] == "pending"
    assert row["attempts"] == 0


# ── claim（FOR UPDATE SKIP LOCKED + due gating）────────────────────────────
async def test_claim_marks_in_flight_then_none(db_session):
    oid = await enqueue_webhook(db_session, url="https://hook.example/x", body={})
    await db_session.commit()

    rec = await _claim_one(db_session)
    assert rec is not None and str(rec["id"]) == oid
    assert (await _row(db_session, oid))["status"] == "in_flight"
    # 沒有其它 pending+due → 再 claim 回 None（不會重複領同一筆）
    assert await _claim_one(db_session) is None


# ── 成功投遞 ───────────────────────────────────────────────────────────────
async def test_mark_delivered(db_session):
    oid = await enqueue_webhook(db_session, url="https://hook.example/x", body={})
    await db_session.commit()
    await _claim_one(db_session)
    await _mark_delivered(db_session, oid, 200)

    row = await _row(db_session, oid)
    assert row["status"] == "delivered"
    assert row["attempts"] == 1
    assert row["last_status_code"] == 200
    assert row["delivered_at"] is not None


# ── 失敗 → 指數退避重排 ─────────────────────────────────────────────────────
async def test_mark_retry_schedules_backoff_and_gates_claim(db_session):
    oid = await enqueue_webhook(db_session, url="https://hook.example/x", body={})
    await db_session.commit()
    await _claim_one(db_session)
    await _mark_retry_or_fail(db_session, oid, attempts=0, error="HTTP 500", sc=500)

    row = await _row(db_session, oid)
    assert row["status"] == "pending"        # 回 pending 等重試
    assert row["attempts"] == 1
    assert row["last_status_code"] == 500
    assert row["in_future"] is True          # next_retry_at 被排到未來（退避）
    # 退避中（next_retry_at > now）→ claim 不該領到（避免狂發）
    assert await _claim_one(db_session) is None
    # 退避約 BACKOFF_SECONDS[0]=60s（給寬鬆窗避免時鐘誤差）
    gap = (await db_session.execute(text(
        "SELECT EXTRACT(EPOCH FROM (next_retry_at - now())) FROM webhook_outbox "
        "WHERE id = CAST(:id AS uuid)"), {"id": oid})).scalar()
    assert BACKOFF_SECONDS[0] - 10 <= float(gap) <= BACKOFF_SECONDS[0] + 5


# ── 重試耗盡 → DLQ(failed) ──────────────────────────────────────────────────
async def test_retry_exhaustion_goes_to_dlq(db_session):
    oid = await enqueue_webhook(db_session, url="https://hook.example/x", body={})
    await db_session.commit()
    await _claim_one(db_session)
    # attempts 已達 MAX_ATTEMPTS-1（最後一次）→ next_attempt == MAX → failed
    await _mark_retry_or_fail(db_session, oid, attempts=MAX_ATTEMPTS - 1,
                              error="HTTP 500", sc=500)
    row = await _row(db_session, oid)
    assert row["status"] == "failed"
    assert row["attempts"] == MAX_ATTEMPTS


# ── due gating + 排序：只領「已到期」的，先到期先領 ─────────────────────────
async def test_claim_picks_due_not_future(db_session):
    due = await enqueue_webhook(db_session, url="https://hook.example/due", body={})
    future = await enqueue_webhook(db_session, url="https://hook.example/future", body={})
    # 把 future 的 next_retry_at 推到未來
    await db_session.execute(text(
        "UPDATE webhook_outbox SET next_retry_at = now() + interval '1 hour' "
        "WHERE id = CAST(:id AS uuid)"), {"id": future})
    await db_session.commit()

    rec = await _claim_one(db_session)
    assert rec is not None and str(rec["id"]) == due   # 只領到期的 due，不碰 future
