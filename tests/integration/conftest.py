"""Service 層整合測試共用 fixture（真 PostgreSQL，非 mock）。

與輕量 CI（landmine 守衛 + 純邏輯單元）分離：這層**需要真 DB + 重依賴**
（sqlalchemy/asyncpg/pytest-asyncio），跑在獨立的 `integration` CI job
（pgvector service container）。

自動 skip 條件（任一不滿足就略過整個目錄、且不 import 重依賴 → 輕量 job 跑
`pytest tests/` 不會炸）：
  1. 沒設環境變數 `STAFFKM_TEST_DB_URL`（本機沒 DB 的人）
  2. 沒裝 sqlalchemy / pytest-asyncio（輕量 CI job 的最小依賴環境）

設計重點：
- 用 repo 真正的 `staffkm_core.utils.database.init_db()` + `_session_factory()`
  → 連同 asyncpg dialect / sqlalchemy async plumbing 一起測（不是另開一個假 engine）。
- schema 用「忠實於 production 的最小 DDL」現建（欄位/型別對齊 `\d` dump），
  避免跑整條 alembic（22 migration、跨服務、慢且脆）；漂移由整合測試本身的
  真 SQL round-trip 擋住（usage.py 的 SQL 一改、欄位不符就紅）。
- 每個 test function 前 TRUNCATE → 測試間零殘留、可任意順序跑。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

TEST_DB_URL = os.environ.get("STAFFKM_TEST_DB_URL")


def _deps_available() -> bool:
    try:
        import pytest_asyncio  # noqa: F401
        import sqlalchemy  # noqa: F401
        return True
    except ImportError:
        return False


# 重依賴 / DB 任一缺 → collection 階段就略過整個目錄（不 import 任何重依賴）。
if not TEST_DB_URL or not _deps_available():
    collect_ignore_glob = ["test_*.py"]
else:
    import pytest_asyncio
    from sqlalchemy import text

    _ROOT = Path(__file__).resolve().parent.parent.parent
    _AGENT = _ROOT / "services" / "agent"
    _CORE = _ROOT / "packages" / "python" / "staffkm-core"
    for _p in (_AGENT, _CORE):
        if str(_p) not in sys.path:
            sys.path.insert(0, str(_p))

    # ── 忠實於 production 的最小 schema（對齊 `\d` dump）─────────────────
    _DDL = """
    CREATE EXTENSION IF NOT EXISTS pgcrypto;

    CREATE TABLE IF NOT EXISTS model_usage_logs (
        id                uuid PRIMARY KEY,
        workspace_id      uuid NOT NULL,
        user_id           uuid,
        application_id    uuid,
        provider_type     varchar(32),
        model             varchar(128),
        prompt_tokens     integer NOT NULL DEFAULT 0,
        completion_tokens integer NOT NULL DEFAULT 0,
        total_tokens      integer NOT NULL DEFAULT 0,
        cost_usd          numeric(12,6) NOT NULL DEFAULT 0,
        latency_ms        integer NOT NULL DEFAULT 0,
        status            varchar(16) NOT NULL DEFAULT 'ok',
        error             text,
        created_at        timestamptz NOT NULL DEFAULT now(),
        unit_type         varchar(16),
        unit_count        numeric(12,4),
        conversation_id   uuid,
        message_id        uuid,
        feature           varchar(16)
    );

    CREATE TABLE IF NOT EXISTS workspace_quotas (
        workspace_id         uuid PRIMARY KEY,
        monthly_token_cap    bigint,
        monthly_cost_cap_usd numeric(12,2),
        updated_at           timestamptz NOT NULL DEFAULT now(),
        updated_by           uuid
    );

    CREATE TABLE IF NOT EXISTS user_quotas (
        workspace_id         uuid NOT NULL,
        user_id              uuid NOT NULL,
        monthly_token_cap    bigint,
        monthly_cost_cap_usd numeric(12,2),
        updated_at           timestamptz NOT NULL DEFAULT now(),
        updated_by           uuid,
        PRIMARY KEY (workspace_id, user_id)
    );

    CREATE TABLE IF NOT EXISTS ai_models (
        id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        model_name              varchar(128) NOT NULL,
        model_type              varchar(32) NOT NULL DEFAULT 'llm',
        price_per_1k_input_usd  numeric(10,6),
        price_per_1k_output_usd numeric(10,6),
        price_per_image_usd     numeric(10,6),
        price_per_second_usd    numeric(10,6),
        price_per_1k_chars_usd  numeric(10,6),
        price_per_call_usd      numeric(10,6)
    );
    """

    _TABLES = ("model_usage_logs", "workspace_quotas", "user_quotas", "ai_models")

    @pytest_asyncio.fixture
    async def db_session():
        """每個 test 一個真 session。

        engine 在「該 test 自己的 event loop」內建（pytest-asyncio 預設每 test 一個
        loop）→ 避免 session-scoped 跨 loop 共用 asyncpg 連線的 InterfaceError。
        schema 用 CREATE ... IF NOT EXISTS 冪等建、TRUNCATE 清殘留。
        """
        from staffkm_core.utils import database as _db

        _db.init_db(TEST_DB_URL)
        # asyncpg 走 prepared statement → 不能一次塞多句；逐句執行。
        async with _db._session_factory() as s:
            for stmt in (x.strip() for x in _DDL.split(";")):
                if stmt:
                    await s.execute(text(stmt))
            await s.execute(text("TRUNCATE " + ", ".join(_TABLES)))
            await s.commit()
        try:
            async with _db._session_factory() as s:
                yield s
                await s.rollback()
        finally:
            await _db._engine.dispose()
