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

    CREATE TABLE IF NOT EXISTS workflow_run_steps (
        id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        run_id          uuid NOT NULL,
        step_index      integer NOT NULL,
        node_key        varchar(64) NOT NULL,
        node_type       varchar(32) NOT NULL,
        status          varchar(16) NOT NULL DEFAULT 'ok',
        input_snapshot  jsonb,
        output_snapshot jsonb,
        error           text,
        attempts        integer NOT NULL DEFAULT 1,
        latency_ms      integer,
        started_at      timestamptz NOT NULL DEFAULT now(),
        finished_at     timestamptz
    );

    CREATE TABLE IF NOT EXISTS webhook_outbox (
        id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        workspace_id     uuid,
        url              text NOT NULL,
        method           varchar(8) NOT NULL DEFAULT 'POST',
        headers          jsonb,
        body             jsonb,
        status           varchar(16) NOT NULL DEFAULT 'pending',
        attempts         integer NOT NULL DEFAULT 0,
        next_retry_at    timestamptz NOT NULL DEFAULT now(),
        last_error       text,
        last_status_code integer,
        created_at       timestamptz NOT NULL DEFAULT now(),
        delivered_at     timestamptz,
        source_type      varchar(32),
        source_id        uuid
    );

    CREATE TABLE IF NOT EXISTS idempotency_keys (
        key           varchar(128) NOT NULL,
        endpoint      varchar(128) NOT NULL,
        workspace_id  uuid,
        response_json jsonb,
        status_code   integer,
        created_at    timestamptz NOT NULL DEFAULT now(),
        expires_at    timestamptz NOT NULL DEFAULT now() + interval '24 hours',
        PRIMARY KEY (key, endpoint)
    );

    -- human_approval / resume 狀態機（pause→approve/reject→resume）
    CREATE TABLE IF NOT EXISTS event_triggers (
        id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        workspace_id   uuid,
        application_id uuid,
        name           varchar(128),
        kind           varchar(16),
        input_template text,
        enabled        boolean DEFAULT true,
        last_status    varchar(16),
        last_error     text,
        created_by     uuid,
        created_at     timestamptz DEFAULT now(),
        updated_at     timestamptz DEFAULT now()
    );

    CREATE TABLE IF NOT EXISTS event_trigger_runs (
        id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        trigger_id     uuid,
        workspace_id   uuid,
        status         varchar(16) DEFAULT 'running',
        fired_at       timestamptz DEFAULT now(),
        finished_at    timestamptz,
        output_summary text,
        error          text,
        paused_at      timestamptz,
        resumed_at     timestamptz,
        resume_node    varchar(64)
    );

    CREATE TABLE IF NOT EXISTS workflow_approvals (
        id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        run_id        uuid,
        workspace_id  uuid,
        node_key      varchar(64),
        status        varchar(16) DEFAULT 'pending',
        requester     varchar(128),
        approver_id   uuid,
        approver_note text,
        payload       jsonb,
        created_at    timestamptz DEFAULT now(),
        resolved_at   timestamptz
    );
    """

    async def _schema(engine):
        await run_ddl(engine, _DDL)

    db_session = make_db_session_fixture(
        _schema,
        truncate_tables=(
            "model_usage_logs", "workspace_quotas", "user_quotas", "ai_models",
            "workflow_run_steps", "webhook_outbox", "idempotency_keys",
            "event_triggers", "event_trigger_runs", "workflow_approvals",
        ),
    )
