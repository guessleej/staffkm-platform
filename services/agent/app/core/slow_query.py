"""Slow SQL query trace — v3.7 P4。

對所有 SQLAlchemy query 計時，超過 SLOW_QUERY_THRESHOLD_MS（預設 500）寫
結構化 log + 加 OTel span tag（如有 active span）。

使用：lifespan 內 import 並 call `install_slow_query_listener(engine)` 一次。
"""
from __future__ import annotations
import os
import time

import structlog
from sqlalchemy import event
from sqlalchemy.engine import Engine

log = structlog.get_logger()

_THRESHOLD_MS = int(os.environ.get("SLOW_QUERY_THRESHOLD_MS", "500"))


def install_slow_query_listener(engine: Engine) -> None:
    """掛兩個 event：cursor_execute before / after，量延遲。

    對 sync 跟 async engine 都適用（async 底層仍走 sync DBAPI cursor）。
    """
    target = getattr(engine, "sync_engine", engine)  # AsyncEngine.sync_engine

    @event.listens_for(target, "before_cursor_execute")
    def _before(conn, cursor, statement, parameters, context, executemany):
        context._slow_query_start = time.monotonic()

    @event.listens_for(target, "after_cursor_execute")
    def _after(conn, cursor, statement, parameters, context, executemany):
        start = getattr(context, "_slow_query_start", None)
        if start is None:
            return
        duration_ms = int((time.monotonic() - start) * 1000)
        if duration_ms < _THRESHOLD_MS:
            return
        # 結構化 log（含完整 SQL + 前 200 字 params）
        sql_preview = statement[:1000].replace("\n", " ").strip()
        params_preview = repr(parameters)[:200] if parameters else ""
        log.warning(
            "slow_query",
            duration_ms=duration_ms,
            threshold_ms=_THRESHOLD_MS,
            sql=sql_preview,
            params=params_preview,
        )
        # 加 OTel span tag（若有 active span）
        try:
            from opentelemetry import trace
            span = trace.get_current_span()
            if span and span.is_recording():
                span.set_attribute("db.slow", True)
                span.set_attribute("db.duration_ms", duration_ms)
                span.set_attribute("db.statement_preview", sql_preview[:200])
        except Exception:
            pass  # OTel 沒啟用就 silent

    log.info("slow_query_listener_installed", threshold_ms=_THRESHOLD_MS)
