"""對話 ownership 跨 user 隔離整合測試（真 PostgreSQL + 真 conversations router）。

補強 landmine 守衛（GatewayHeadersMiddleware 有沒有註冊）的**執行面**：把真的
`app.api.conversations.router` 掛進 FastAPI app + 一個鏡像 GatewayHeadersMiddleware
（從 X-User-ID 寫 request.state.user_id），用 httpx ASGITransport 以「不同身分」打進去，
證明 user A **讀不到 / 刪不了 / 分享不了** user B 的對話。

v5.7.2 補過 delete 的 ownership（之前任何人都能刪別人對話）；v5.9.13 補過 chat 的
GatewayHeadersMiddleware（之前 user_id 全 fallback 'anonymous'）。本檔把這些隔離不變式釘死。
"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.models.conversation import Conversation, Message

pytestmark = pytest.mark.asyncio

_PREFIX = "/api/v1/chat/conversations"


def _make_app():
    from fastapi import FastAPI
    from starlette.middleware.base import BaseHTTPMiddleware

    from app.api.conversations import router

    class _GatewayHeaders(BaseHTTPMiddleware):  # 鏡像 chat/main.py 的 GatewayHeadersMiddleware
        async def dispatch(self, request, call_next):
            request.state.user_id = request.headers.get("X-User-ID") or None
            request.state.roles = []
            return await call_next(request)

    app = FastAPI()
    app.add_middleware(_GatewayHeaders)
    app.include_router(router, prefix=_PREFIX)
    return app


def _client(app, user_id):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t",
                       headers={"X-User-ID": user_id})


async def _seed_conv(session, user_id, *, title="t", with_message=False) -> str:
    conv = Conversation(user_id=user_id, scenario_id="s1", title=title)
    session.add(conv)
    await session.commit()
    await session.refresh(conv)
    if with_message:
        session.add(Message(conversation_id=conv.id, role="user", content=f"secret of {user_id}"))
        await session.commit()
    return str(conv.id)


async def _is_active(session, cid) -> bool:
    return (await session.execute(text(
        "SELECT is_active FROM conversations WHERE id = CAST(:id AS uuid)"), {"id": cid})).scalar()


# ── 列表：只看得到自己的 ─────────────────────────────────────────────────
async def test_list_shows_only_own(db_session):
    a = await _seed_conv(db_session, "user-a", title="A's")
    b = await _seed_conv(db_session, "user-b", title="B's")
    app = _make_app()
    async with _client(app, "user-a") as c:
        r = await c.get(_PREFIX)
    ids = [row["id"] for row in r.json()["data"]]
    assert a in ids and b not in ids       # A 只看到 A 的，看不到 B 的


# ── 刪除：刪不了別人的（403），刪得了自己的 ───────────────────────────────
async def test_delete_others_forbidden(db_session):
    b = await _seed_conv(db_session, "user-b")
    app = _make_app()
    async with _client(app, "user-a") as c:
        r = await c.delete(f"{_PREFIX}/{b}")
    assert r.status_code == 403
    assert await _is_active(db_session, b) is True   # B 的對話沒被刪


async def test_delete_own_ok(db_session):
    a = await _seed_conv(db_session, "user-a")
    app = _make_app()
    async with _client(app, "user-a") as c:
        r = await c.delete(f"{_PREFIX}/{a}")
    assert r.status_code == 200
    assert await _is_active(db_session, a) is False  # soft delete 生效


# ── 讀訊息：讀不到別人的（防 IDOR）──────────────────────────────────────────
async def test_get_messages_cross_user_denied(db_session):
    b = await _seed_conv(db_session, "user-b", with_message=True)
    app = _make_app()
    async with _client(app, "user-a") as c:
        r = await c.get(f"{_PREFIX}/{b}/messages")
    # A 不該讀到 B 的對話內容（403 無權 / 404 不存在 皆可，重點是「拿不到 B 的 secret」）
    assert r.status_code in (403, 404)


# ── 分享：分享不了別人的（403）─────────────────────────────────────────────
async def test_share_others_forbidden(db_session):
    b = await _seed_conv(db_session, "user-b")
    app = _make_app()
    async with _client(app, "user-a") as c:
        r = await c.post(f"{_PREFIX}/{b}/share")
    assert r.status_code == 403
