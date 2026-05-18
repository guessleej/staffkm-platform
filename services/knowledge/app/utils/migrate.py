"""Alembic upgrade runner — lifespan 用。

在 service 啟動時跑 alembic upgrade head，把任何待 apply 的 revision 帶上來。
baseline (0001_baseline) 是 no-op；schema 由既有 bootstrap_ddl 接管。
未來新 schema 改動請新增 alembic revision 走這條路。
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import structlog
from alembic import command
from alembic.config import Config

log = structlog.get_logger()


def _upgrade_sync() -> None:
    cfg_path = Path(__file__).resolve().parents[2] / "alembic.ini"
    cfg = Config(str(cfg_path))
    command.upgrade(cfg, "head")


async def run_alembic_upgrade() -> None:
    try:
        await asyncio.to_thread(_upgrade_sync)
        log.info("alembic_upgrade_ok")
    except Exception as e:
        log.warning("alembic_upgrade_failed", error=str(e))
