"""auth service 整合測試 fixture（真 PostgreSQL）。

schema 直接用 ORM `User.__table__` 現建 → **忠實於 model 定義、零 DDL 漂移**
（auth 走 SQLAlchemy ORM，不像 agent quota 走 raw SQL）。

沒設 STAFFKM_TEST_DB_URL 或沒裝重依賴 → 整個目錄自動 skip 且不 top-level import 重依賴。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_TEST_DB_URL = os.environ.get("STAFFKM_TEST_DB_URL")


def _deps() -> bool:
    try:
        import passlib  # noqa: F401  （auth 額外依賴）
        import pytest_asyncio  # noqa: F401
        import sqlalchemy  # noqa: F401
        return True
    except ImportError:
        return False


if not _TEST_DB_URL or not _deps():
    collect_ignore_glob = ["test_*.py"]
else:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # tests/integration（for _harness）
    from sqlalchemy import text

    from _harness import add_service_paths, make_db_session_fixture

    add_service_paths("auth")

    async def _schema(engine):
        # pgcrypto 供 gen_random_uuid（保險）；users 表由 ORM metadata 現建。
        from app.models.user import User

        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
            await conn.run_sync(lambda c: User.__table__.create(c, checkfirst=True))

    db_session = make_db_session_fixture(_schema, truncate_tables=("users",))
