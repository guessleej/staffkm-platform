"""Alembic env — staffKM auth service。

從 app.config.settings.DB_URL 讀連線；async URL（postgresql+asyncpg://）
會被轉成 sync URL（postgresql://）給 alembic 用 psycopg2-style driver。

online 模式用 pg_advisory_lock 包住 upgrade，避免多 instance 同時跑 migration。
"""
from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text

from app.config import settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None

_SERVICE = "auth"


def _sync_url(url: str) -> str:
    url = (
        url.replace("postgresql+asyncpg://", "postgresql://")
        .replace("postgres+asyncpg://", "postgresql://")
    )
    # asyncpg uses ?ssl=disable; psycopg2 uses ?sslmode=disable
    url = url.replace("?ssl=disable", "?sslmode=disable").replace("&ssl=disable", "&sslmode=disable")
    url = url.replace("?ssl=require", "?sslmode=require").replace("&ssl=require", "&sslmode=require")
    return url


def run_migrations_offline() -> None:
    url = _sync_url(settings.DB_URL)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        version_table='alembic_version_auth',
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    cfg = config.get_section(config.config_ini_section) or {}
    cfg["sqlalchemy.url"] = _sync_url(settings.DB_URL)
    connectable = engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    lock_sql = text(f"SELECT pg_advisory_lock(hashtext('staffkm_migrate_{_SERVICE}'))")
    unlock_sql = text(f"SELECT pg_advisory_unlock(hashtext('staffkm_migrate_{_SERVICE}'))")

    with connectable.connect() as connection:
        # 用 AUTOCOMMIT：advisory_lock / unlock 不能在 transaction 內
        # 而且 alembic 的 begin_transaction 會自己管 inner transaction commit
        connection = connection.execution_options(isolation_level="AUTOCOMMIT")
        connection.execute(lock_sql)
        try:
            context.configure(connection=connection, target_metadata=target_metadata, version_table='alembic_version_auth')
            with context.begin_transaction():
                context.run_migrations()
        finally:
            connection.execute(unlock_sql)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
