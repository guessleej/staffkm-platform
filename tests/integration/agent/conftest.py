"""agent service 整合測試 fixture（真 PostgreSQL）。

沒設 STAFFKM_TEST_DB_URL 或沒裝重依賴 → 整個目錄自動 skip 且不 top-level import
重依賴（輕量 backend job 跑 `pytest tests/` 不受影響）。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_TEST_DB_URL = os.environ.get("STAFFKM_TEST_DB_URL")


def _deps() -> bool:
    try:
        import pytest_asyncio  # noqa: F401
        import sqlalchemy  # noqa: F401
        return True
    except ImportError:
        return False


if not _TEST_DB_URL or not _deps():
    collect_ignore_glob = ["test_*.py"]
else:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # tests/integration（for _harness）
    from _harness import add_service_paths, make_db_session_fixture, run_ddl

    add_service_paths("agent")

    # 忠實於 production 的最小 schema（對齊 `\d` dump）
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

    async def _schema(engine):
        await run_ddl(engine, _DDL)

    db_session = make_db_session_fixture(
        _schema,
        truncate_tables=("model_usage_logs", "workspace_quotas", "user_quotas", "ai_models"),
    )
