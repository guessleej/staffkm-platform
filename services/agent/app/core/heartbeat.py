"""Worker heartbeat — v3.6 P2。

每個 worker loop 在開頭 call `await safe_beat(...)`。
admin 透過 task_heartbeats 表觀測 worker 健康。

last_beat 超過 5 min → 視為 stale（admin UI / Grafana 顯紅）。
"""
from __future__ import annotations
import os
import socket

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger()

_HOST = socket.gethostname()
_PID = os.getpid()
_started: dict[str, str] = {}


async def beat(session: AsyncSession, *, worker_name: str, in_flight: int = 0) -> None:
    """UPSERT 一筆 heartbeat。第一次 call 寫入 started_at；之後只更 last_beat / in_flight。"""
    if worker_name not in _started:
        await session.execute(text("""
            INSERT INTO task_heartbeats (worker_name, pid, host, started_at, last_beat, in_flight)
            VALUES (:n, :p, :h, now(), now(), :inf)
            ON CONFLICT (worker_name) DO UPDATE
            SET pid = EXCLUDED.pid,
                host = EXCLUDED.host,
                started_at = now(),
                last_beat = now(),
                in_flight = EXCLUDED.in_flight
        """), {"n": worker_name, "p": _PID, "h": _HOST, "inf": in_flight})
        _started[worker_name] = "1"
    else:
        await session.execute(text("""
            UPDATE task_heartbeats
            SET last_beat = now(), in_flight = :inf, pid = :p, host = :h
            WHERE worker_name = :n
        """), {"n": worker_name, "p": _PID, "h": _HOST, "inf": in_flight})
    await session.commit()


async def safe_beat(session_factory_getter, *, worker_name: str, in_flight: int = 0) -> None:
    """背景 loop 用：每輪 call；失敗只 log 不中斷。

    session_factory_getter 與既有 worker 簽名一致（callable() → session_factory 或 None）。
    """
    try:
        sf = session_factory_getter() if callable(session_factory_getter) else session_factory_getter
        if sf is None:
            return
        async with sf() as session:
            await beat(session, worker_name=worker_name, in_flight=in_flight)
    except Exception as e:
        log.warning("heartbeat_failed", worker=worker_name, error=str(e))
