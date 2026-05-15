"""非同步資料庫連線工廠"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_engine = None
_session_factory = None


def init_db(db_url: str, echo: bool = False):
    global _engine, _session_factory
    _engine = create_async_engine(db_url, echo=echo, pool_size=10, max_overflow=20)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)


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
