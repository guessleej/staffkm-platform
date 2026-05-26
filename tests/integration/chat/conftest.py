"""chat service 整合測試 fixture（真 PostgreSQL）。

schema 從 ORM `Conversation` / `Message` metadata 現建（零 DDL 漂移）。

沒設 STAFFKM_TEST_DB_URL 或沒裝重依賴（含 fastapi）→ 整個目錄自動 skip 且不 top-level
import 重依賴。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_TEST_DB_URL = os.environ.get("STAFFKM_TEST_DB_URL")


def _deps() -> bool:
    try:
        import fastapi  # noqa: F401  （掛 conversations router 用）
        import pytest_asyncio  # noqa: F401
        import sqlalchemy  # noqa: F401
        return True
    except ImportError:
        return False


if not _TEST_DB_URL or not _deps():
    collect_ignore_glob = ["test_*.py"]
else:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # tests/integration（for _harness）
    from _harness import add_service_paths, make_db_session_fixture

    add_service_paths("chat")

    async def _schema(engine):
        from app.models.conversation import Conversation, Message

        async with engine.begin() as conn:
            await conn.run_sync(
                lambda c: Conversation.metadata.create_all(
                    c, tables=[Conversation.__table__, Message.__table__], checkfirst=True
                )
            )

    db_session = make_db_session_fixture(_schema, truncate_tables=("messages", "conversations"))
