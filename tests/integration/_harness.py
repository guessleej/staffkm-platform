"""整合測試共用 harness。

⚠ 只在各 subdir conftest 的「依賴/DB 都就緒」guard 區塊內 import（本檔 top-level 會
import sqlalchemy/pytest-asyncio）→ 輕量 backend job（最小依賴）跑 `pytest tests/` 時，
各 subdir conftest 的 guard 會先 collect_ignore、不會走到這裡。

為什麼分 subdir：auth / agent / knowledge 各自都有 `app/` package，同一個 pytest
process 只能把一個 service 放上 sys.path（否則 `import app.core.X` 撞名）。所以
`tests/integration/{service}/` 一個資料夾一個 service，CI 每個 subdir 各自一次
pytest invocation（與 backend job 拆 knowledge/agent 同理）。
"""
from __future__ import annotations

import os
import sys
from collections.abc import Awaitable, Callable, Iterable
from pathlib import Path

import pytest_asyncio
from sqlalchemy import text

_ROOT = Path(__file__).resolve().parent.parent.parent
_CORE = _ROOT / "packages" / "python" / "staffkm-core"


def add_service_paths(*service_dirnames: str) -> None:
    """把指定 service 目錄 + staffkm-core 加到 sys.path（service 在最前）。

    一個 process 只放一個 service（見檔頭說明）。
    """
    for p in [_ROOT / "services" / name for name in service_dirnames] + [_CORE]:
        sp = str(p)
        if sp not in sys.path:
            sys.path.insert(0, sp)


async def run_ddl(engine, ddl: str) -> None:
    """逐句跑 DDL（asyncpg prepared statement 不能一次多句）。"""
    async with engine.begin() as conn:
        for stmt in (x.strip() for x in ddl.split(";")):
            if stmt:
                await conn.execute(text(stmt))


def make_db_session_fixture(
    schema_setup: Callable[[object], Awaitable[None]],
    truncate_tables: Iterable[str] = (),
):
    """產生 function-scoped `db_session` fixture。

    - 用 repo 真正的 `init_db()` + `_session_factory()`（連 asyncpg dialect 一起測）。
    - engine 在「該 test 自己的 event loop」內建 → 避免 pytest-asyncio 跨 loop 共用
      asyncpg 連線的 InterfaceError。
    - `schema_setup(engine)`：冪等建表（DDL 或 ORM metadata）。
    - 測前 TRUNCATE → 測試間零殘留、可任意順序。
    """
    truncate = tuple(truncate_tables)

    @pytest_asyncio.fixture
    async def db_session():
        from staffkm_core.utils import database as _db

        _db.init_db(os.environ["STAFFKM_TEST_DB_URL"])
        await schema_setup(_db._engine)
        if truncate:
            async with _db._session_factory() as s:
                await s.execute(text("TRUNCATE " + ", ".join(truncate)))
                await s.commit()
        try:
            async with _db._session_factory() as s:
                yield s
                await s.rollback()
        finally:
            await _db._engine.dispose()

    return db_session


def deps_and_db_ready() -> bool:
    """guard：DB env 有設 + 重依賴裝了。供各 subdir conftest 在 import harness 前自己 inline 判斷。"""
    if not os.environ.get("STAFFKM_TEST_DB_URL"):
        return False
    try:
        import pytest_asyncio  # noqa: F401
        import sqlalchemy  # noqa: F401
        return True
    except ImportError:
        return False
