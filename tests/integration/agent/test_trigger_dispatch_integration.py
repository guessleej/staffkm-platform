"""Trigger dispatcher 至少一次 + 去重整合測試（真 PostgreSQL）。

跟 webhook_outbox 同類，但在「事件觸發**進來**」那端：event_trigger_runs 以 status
轉移 + `FOR UPDATE SKIP LOCKED` 保證**同一筆 run 不被兩個 dispatcher 副本同時處理**
（多副本去重 / exactly-one-processes）。

守：
- claim 把 queued → running（FIFO：先 fired 先處理）。
- 只 claim queued（running/ok/paused 不再被撈）→ 不重複處理。
- **並發兩個 dispatcher 搶同一筆 → 只有一個拿到，另一個 None**（SKIP LOCKED 去重核心）。
"""
from __future__ import annotations

import asyncio
import uuid

import pytest
from sqlalchemy import text

from app.core.trigger_dispatcher import _claim_one
from staffkm_core.utils import database as _db

pytestmark = pytest.mark.asyncio


def _ws() -> str:
    return str(uuid.uuid4())


async def _enqueue(session, ws, *, status="queued", fired_offset_sec=0) -> str:
    """建 trigger + 一筆 run（預設 queued、fired_at=now()+offset）。回 run_id。"""
    trigger_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    await session.execute(text(
        "INSERT INTO event_triggers (id, workspace_id, application_id, name, kind) "
        "VALUES (CAST(:t AS uuid), CAST(:ws AS uuid), CAST(:a AS uuid), 'trg', 'manual')"),
        {"t": trigger_id, "ws": ws, "a": str(uuid.uuid4())})
    await session.execute(text(
        "INSERT INTO event_trigger_runs (id, trigger_id, workspace_id, status, fired_at) "
        "VALUES (CAST(:r AS uuid), CAST(:t AS uuid), CAST(:ws AS uuid), :st, "
        "        now() + make_interval(secs => :off))"),
        {"r": run_id, "t": trigger_id, "ws": ws, "st": status, "off": fired_offset_sec})
    await session.commit()
    return run_id


async def _status(session, run_id) -> str:
    return (await session.execute(text(
        "SELECT status FROM event_trigger_runs WHERE id = CAST(:r AS uuid)"),
        {"r": run_id})).scalar()


# ── claim：queued → running ────────────────────────────────────────────────
async def test_claim_transitions_queued_to_running(db_session):
    ws = _ws()
    run_id = await _enqueue(db_session, ws)
    rec = await _claim_one(db_session)
    assert rec is not None and str(rec["run_id"]) == run_id
    assert await _status(db_session, run_id) == "running"
    # 已 running → 沒有其它 queued → 再 claim 回 None（不重複處理）
    assert await _claim_one(db_session) is None


# ── FIFO：先 fired 先處理 ───────────────────────────────────────────────────
async def test_claim_is_fifo(db_session):
    ws = _ws()
    older = await _enqueue(db_session, ws, fired_offset_sec=-30)
    newer = await _enqueue(db_session, ws, fired_offset_sec=0)
    first = await _claim_one(db_session)
    second = await _claim_one(db_session)
    assert str(first["run_id"]) == older     # 先 fired 的先被撈
    assert str(second["run_id"]) == newer


# ── 只 claim queued（running 不再被撈）──────────────────────────────────────
async def test_non_queued_not_claimed(db_session):
    ws = _ws()
    await _enqueue(db_session, ws, status="running")
    await _enqueue(db_session, ws, status="ok")
    await _enqueue(db_session, ws, status="paused")
    assert await _claim_one(db_session) is None   # 沒有 queued → 撈不到


# ── 並發去重：兩個 dispatcher 搶同一筆 → 只有一個拿到 ──────────────────────
async def test_concurrent_claim_no_double_process(db_session):
    ws = _ws()
    run_id = await _enqueue(db_session, ws)

    async def _claim_isolated():
        async with _db._session_factory() as s:   # 各自獨立連線，鏡像多 dispatcher 副本
            return await _claim_one(s)

    r1, r2 = await asyncio.gather(_claim_isolated(), _claim_isolated())
    got = [r for r in (r1, r2) if r is not None]
    assert len(got) == 1                          # 只有一個副本拿到（SKIP LOCKED 去重）
    assert str(got[0]["run_id"]) == run_id
    assert await _status(db_session, run_id) == "running"


# ── reaper：crash 殘留的殭屍 run 回收（v5.12）─────────────────────────────────
async def test_reaper_recovers_stale_running(db_session):
    """fired >15min 前仍 running → 視為前一個 process crash/腰斬的殭屍 → 回收 queued。"""
    from app.core.trigger_dispatcher import reap_stale_runs
    ws = _ws()
    run_id = await _enqueue(db_session, ws, status="running", fired_offset_sec=-1200)  # 20min 前
    n = await reap_stale_runs(_db._session_factory)
    assert n >= 1
    assert await _status(db_session, run_id) == "queued"      # 被回收重排


async def test_reaper_leaves_fresh_running(db_session):
    """剛 fired、仍 running → 進行中，多副本下不可誤回收（用 fired_at 判 stale 的關鍵不變式）。"""
    from app.core.trigger_dispatcher import reap_stale_runs
    ws = _ws()
    run_id = await _enqueue(db_session, ws, status="running", fired_offset_sec=-60)  # 1min 前
    await reap_stale_runs(_db._session_factory)
    assert await _status(db_session, run_id) == "running"     # 不動


async def test_reaper_ignores_non_running(db_session):
    """非 running 的舊 run（paused 為合法非終態）不可被回收。"""
    from app.core.trigger_dispatcher import reap_stale_runs
    ws = _ws()
    paused = await _enqueue(db_session, ws, status="paused", fired_offset_sec=-1200)
    await reap_stale_runs(_db._session_factory)
    assert await _status(db_session, paused) == "paused"      # 不動
