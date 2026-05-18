"""Slow SQL query trace — v3.7 P4 / v3.8 P4。

對所有 SQLAlchemy query 計時，超過 SLOW_QUERY_THRESHOLD_MS（預設 500）寫
結構化 log + 加 OTel span tag（如有 active span）。

v3.8 P4：偵測到 slow 時，自動 spawn async task 跑 EXPLAIN (ANALYZE) 把 plan
寫進 `slow_query_explains` table，admin 可在 UI 看完整 plan。
- env `SLOW_QUERY_CAPTURE_EXPLAIN`（預設 'true'）關閉時不 capture
- guard：sql 開頭 `EXPLAIN` 直接跳過 listener，避免 EXPLAIN 自己又被偵測
- 同一個 sql_hash 在 5 分鐘內只 capture 一次（in-memory dedup，避免風暴）
- 對 SELECT 才 ANALYZE，其他語句只 EXPLAIN（避免 INSERT/UPDATE/DELETE 被真執行）
- 含 bind params 的 query 不 inline EXPLAIN，僅紀錄 sql + duration

使用：lifespan 內 import 並 call `install_slow_query_listener(engine)` 一次。
"""
from __future__ import annotations
import asyncio
import hashlib
import json as _json
import os
import time

import structlog
from sqlalchemy import event
from sqlalchemy.engine import Engine

log = structlog.get_logger()

_THRESHOLD_MS = int(os.environ.get("SLOW_QUERY_THRESHOLD_MS", "500"))

# in-memory dedup cache: sql_hash -> last_captured_monotonic_ts
_recent_captures: dict[str, float] = {}
_CAPTURE_TTL_SEC = 300


def _normalize_sql(sql: str) -> str:
    """簡單 normalize：去前後空白、collapse whitespace。"""
    return " ".join(sql.split())


def _sql_hash(sql: str) -> str:
    return hashlib.sha256(_normalize_sql(sql).encode()).hexdigest()[:32]


async def _capture_explain(sql: str, params, duration_ms: int) -> None:
    """跑 EXPLAIN (ANALYZE, FORMAT JSON) 寫 DB。失敗只 log warn。"""
    try:
        from staffkm_core.utils import database as _db
    except Exception:
        return
    if getattr(_db, "_session_factory", None) is None:
        return

    h = _sql_hash(sql)
    now = time.monotonic()
    last = _recent_captures.get(h, 0)
    if now - last < _CAPTURE_TTL_SEC:
        return
    _recent_captures[h] = now

    explain_json = None
    explain_err = None
    try:
        from sqlalchemy import text as _text
        sql_stripped = sql.strip().upper()
        if not sql_stripped.startswith("SELECT"):
            # 不對 DML 跑 ANALYZE（會真執行一次），只取 plan
            explain_kind = "EXPLAIN (FORMAT JSON)"
        else:
            explain_kind = "EXPLAIN (ANALYZE, FORMAT JSON)"

        # 含 bind params 的 query 不安全 inline 進 EXPLAIN，跳過 plan，只紀錄 sql。
        if params:
            explain_json = {"_skipped": "query had bind params, can't safely EXPLAIN ANALYZE"}
        else:
            async with _db._session_factory() as session:
                r = await session.execute(_text(f"{explain_kind} {sql}"))
                rows = r.fetchall()
                if rows and rows[0][0]:
                    explain_json = rows[0][0]  # PG 回的就是 JSON
    except Exception as e:
        explain_err = str(e)[:500]

    try:
        from sqlalchemy import text as _text
        async with _db._session_factory() as session:
            await session.execute(_text("""
                INSERT INTO slow_query_explains (
                    duration_ms, sql_text, sql_hash, explain_json, explain_error
                ) VALUES (
                    :ms, :sql, :h, CAST(:plan AS jsonb), :err
                )
            """), {
                "ms": duration_ms,
                "sql": sql[:4000],
                "h": h,
                "plan": _json.dumps(explain_json) if explain_json else None,
                "err": explain_err,
            })
            await session.commit()
        log.info("slow_query_explain_captured", hash=h[:8], duration_ms=duration_ms)
    except Exception as e:
        log.warning("slow_query_explain_persist_failed", error=str(e))


def _schedule_capture(sql: str, params, duration_ms: int) -> None:
    """在 sync listener context 安全 schedule async capture。

    SQLAlchemy event listener 是 sync callback。當底層 engine 是 AsyncEngine
    時，listener 觸發時通常仍在 running loop 內（greenlet bridge）；偶爾在
    純 sync engine context 則拿不到 loop，此時就 silent skip——這只是觀測
    功能，不該拖慢實際 query path。
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return  # 沒有 running loop（純 sync engine 或 worker thread），跳過
    try:
        loop.create_task(_capture_explain(sql, params, duration_ms))
    except Exception:
        pass


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

        # v3.8 P4：guard — 不要讓 EXPLAIN 自己又被 capture（無限遞迴 / 風暴）
        stripped_upper = statement.lstrip().upper()
        if stripped_upper.startswith("EXPLAIN") or stripped_upper.startswith("INSERT INTO SLOW_QUERY_EXPLAINS"):
            return
        if os.environ.get("SLOW_QUERY_CAPTURE_EXPLAIN", "true").lower() == "true":
            _schedule_capture(statement, parameters, duration_ms)

    log.info("slow_query_listener_installed", threshold_ms=_THRESHOLD_MS)
