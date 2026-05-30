"""Idempotency-Key 中介層整合測試（真 PostgreSQL + 真 ASGI app）。

守的是去重 resilience：同一 Idempotency-Key + endpoint 在 24h 內，第二次請求**不重跑
handler**、直接回上次的 response（避免重複扣款 / 重複觸發 / 重複送通知）。

用 minimal Starlette app 掛真的 `IdempotencyMiddleware`，經 httpx ASGITransport 打進去，
中介層用 `_db._session_factory`（db_session fixture 已 init_db）對真 PG 讀寫 idempotency_keys。
handler 帶 call counter → 直接驗「第二次有沒有真的跳過 handler」。
"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from app.middleware.idempotency import IdempotencyMiddleware

pytestmark = pytest.mark.asyncio


def _make_app():
    """minimal app：counter 記 handler 跑幾次；多個路徑涵蓋 streaming/JSON。"""
    state = {"things": 0, "run": 0}

    async def things(request):       # 一般 JSON POST → 可去重
        state["things"] += 1
        return JSONResponse({"n": state["things"]})

    async def run(request):          # 路徑含 /run → _is_streaming → 不去重
        state["run"] += 1
        return JSONResponse({"n": state["run"]})

    app = Starlette(routes=[
        Route("/api/v1/things", things, methods=["POST", "GET"]),
        Route("/api/v1/run/x", run, methods=["POST"]),
    ])
    app.add_middleware(IdempotencyMiddleware)
    return app, state


def _client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


async def _count_keys(session):
    return (await session.execute(text("SELECT count(*) FROM idempotency_keys"))).scalar()


# ── 同 key 第二次 → 跳過 handler、回快取 ──────────────────────────────────
async def test_same_key_replays_and_skips_handler(db_session):
    app, state = _make_app()
    async with _client(app) as c:
        r1 = await c.post("/api/v1/things", headers={"Idempotency-Key": "k1"})
        r2 = await c.post("/api/v1/things", headers={"Idempotency-Key": "k1"})

    assert r1.json() == {"n": 1} and r1.status_code == 200
    assert r2.json() == {"n": 1}                       # 回放上次結果，非 {"n":2}
    assert r2.headers.get("Idempotency-Replayed") == "true"
    assert state["things"] == 1                         # handler 只跑一次（第二次被擋）
    assert await _count_keys(db_session) == 1


# ── 不同 key → 各自跑 ──────────────────────────────────────────────────────
async def test_different_keys_both_run(db_session):
    app, state = _make_app()
    async with _client(app) as c:
        await c.post("/api/v1/things", headers={"Idempotency-Key": "a"})
        r = await c.post("/api/v1/things", headers={"Idempotency-Key": "b"})
    assert r.json() == {"n": 2}
    assert state["things"] == 2


# ── 無 key → 不攔截（每次都跑）─────────────────────────────────────────────
async def test_no_key_not_intercepted(db_session):
    app, state = _make_app()
    async with _client(app) as c:
        await c.post("/api/v1/things")
        r = await c.post("/api/v1/things")
    assert r.json() == {"n": 2}
    assert state["things"] == 2
    assert await _count_keys(db_session) == 0          # 沒 key → 不落 idempotency row


# ── GET 不攔截（只攔 POST）─────────────────────────────────────────────────
async def test_get_not_intercepted(db_session):
    app, state = _make_app()
    async with _client(app) as c:
        await c.get("/api/v1/things", headers={"Idempotency-Key": "k"})
        await c.get("/api/v1/things", headers={"Idempotency-Key": "k"})
    assert state["things"] == 2


# ── streaming endpoint（路徑含 /run）→ 不快取（每次都跑）────────────────────
async def test_streaming_path_not_cached(db_session):
    app, state = _make_app()
    async with _client(app) as c:
        await c.post("/api/v1/run/x", headers={"Idempotency-Key": "same"})
        r = await c.post("/api/v1/run/x", headers={"Idempotency-Key": "same"})
    assert r.json() == {"n": 2}                         # 沒被去重
    assert state["run"] == 2
    assert await _count_keys(db_session) == 0


# ── SSE accept header → 不快取 ─────────────────────────────────────────────
async def test_sse_accept_not_cached(db_session):
    app, state = _make_app()
    async with _client(app) as c:
        h = {"Idempotency-Key": "s", "accept": "text/event-stream"}
        await c.post("/api/v1/things", headers=h)
        r = await c.post("/api/v1/things", headers=h)
    assert r.json() == {"n": 2}
    assert state["things"] == 2


# ── 並發同 key → advisory lock 原子保留：handler 只跑一次（v5.12 P0）──────────
async def test_concurrent_same_key_runs_handler_once(db_session):
    """證明上輪 advisory lock 修復：兩個並發同 Idempotency-Key 請求，handler 只執行一次。
    原本 lookup→run 無保留 → 兩個都 miss、都跑 handler（對非冪等寫入＝重複副作用）。"""
    import asyncio

    state = {"n": 0}

    async def slow(request):
        state["n"] += 1
        await asyncio.sleep(0.3)  # 撐開臨界區，讓兩個並發請求真正重疊
        return JSONResponse({"n": state["n"]})

    app = Starlette(routes=[Route("/api/v1/pay", slow, methods=["POST"])])
    app.add_middleware(IdempotencyMiddleware)

    async with _client(app) as c:
        r1, r2 = await asyncio.gather(
            c.post("/api/v1/pay", headers={"Idempotency-Key": "same"}),
            c.post("/api/v1/pay", headers={"Idempotency-Key": "same"}),
        )
    assert state["n"] == 1                         # advisory lock 序列化 → handler 只跑一次
    assert r1.json() == r2.json() == {"n": 1}      # 兩個回應一致
    assert await _count_keys(db_session) == 1
