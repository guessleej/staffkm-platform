"""Trial expiry worker — v4.1 A。

每小時掃一次 workspace 表：把過期但未凍結的 trial workspace 標 is_frozen=TRUE。
真正阻擋寫入的邏輯（middleware / endpoint check）留給後續 v4.x；此 worker
只負責標記，admin 透過既有 admin/quotas 介面可看到 frozen 狀態。

對齊 v3.6 worker pattern：safe_beat → SELECT for update → log；不阻塞 lifespan。
"""
from __future__ import annotations
import asyncio

import structlog
from sqlalchemy import text

log = structlog.get_logger()


async def _freeze_expired(session) -> int:
    r = await session.execute(text("""
        UPDATE workspace
        SET is_frozen = TRUE
        WHERE trial_expires_at < now()
          AND trial_plan IS NOT NULL
          AND is_frozen = FALSE
        RETURNING id
    """))
    rows = r.fetchall()
    await session.commit()
    return len(rows)


async def trial_expiry_loop(session_factory_getter, interval_sec: int = 3600):
    """背景 loop：每 interval_sec 跑一次 _freeze_expired。"""
    from app.core.heartbeat import safe_beat
    while True:
        await safe_beat(session_factory_getter, worker_name="trial_expiry_worker")  # noqa
        try:
            sf = session_factory_getter()
            if sf is not None:
                async with sf() as session:
                    n = await _freeze_expired(session)
                    if n > 0:
                        log.info("trial_workspaces_frozen", count=n)
        except Exception as e:
            log.error("trial_expiry_loop_failed", error=str(e))
        await asyncio.sleep(interval_sec)
