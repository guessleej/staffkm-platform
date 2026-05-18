"""非同步資料庫連線工廠

v4.0 P6: 支援 optional read replica pool。
- `init_db(db_url)`         — v3.x 行為（讀寫共用同一個 pool）
- `init_db(db_url, read_url)` — 多開一個 read-only pool，讀重的 endpoint 用
  `Depends(get_read_session)` 走 replica；未設則 fallback 主 pool。
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_engine = None
_session_factory = None
# v4.0 P6: read replica pool（optional）
_read_engine = None
_read_session_factory = None


def init_db(db_url: str, read_url: str | None = None, echo: bool = False):
    """初始化 DB engine。

    v4.0 P6: `read_url` 不設或等於 `db_url` → 維持原行為（單 pool）。
    設了不同的 URL → 額外開 read pool，給 `get_read_session()` 用。
    """
    global _engine, _session_factory, _read_engine, _read_session_factory
    _engine = create_async_engine(db_url, echo=echo, pool_size=10, max_overflow=20)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    if read_url and read_url != db_url:
        _read_engine = create_async_engine(read_url, echo=echo, pool_size=10, max_overflow=20)
        _read_session_factory = async_sessionmaker(_read_engine, expire_on_commit=False)
    else:
        _read_engine = None
        _read_session_factory = None


async def get_session() -> AsyncSession:
    if _session_factory is None:
        raise RuntimeError("資料庫尚未初始化，請先呼叫 init_db()")
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_read_session() -> AsyncSession:
    """v4.0 P6: read-only session；走 read replica（沒設則 fallback 主 pool）。

    使用時機：純查詢、報表類 endpoint（admin_billing、analytics、search 等）。
    不會 commit，session 直接 close — 不適合任何寫入操作。
    """
    sf = _read_session_factory or _session_factory
    if sf is None:
        raise RuntimeError("資料庫尚未初始化，請先呼叫 init_db()")
    async with sf() as session:
        try:
            yield session
        finally:
            await session.close()
