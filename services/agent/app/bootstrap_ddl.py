"""啟動時 idempotent DDL — 為 agent service 涉及的表加上 workspace_id。

對應 RFC-001 Stage 2：所有業務表必須具備 workspace_id 欄位 + 索引，
並把既有 row backfill 到 default workspace（由 0001_workspace.sql 預先建立）。
"""
import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings

log = structlog.get_logger()

DEFAULT_WORKSPACE_ID = "00000000-0000-0000-0000-000000000001"


# asyncpg 一次只能執行單一 statement，故拆成清單依序執行
_BOOTSTRAP_STATEMENTS: list[str] = [
    # ── applications ────────────────────────────────────────────────────────
    "ALTER TABLE applications ADD COLUMN IF NOT EXISTS workspace_id UUID",
    f"UPDATE applications SET workspace_id = '{DEFAULT_WORKSPACE_ID}' WHERE workspace_id IS NULL",
    "CREATE INDEX IF NOT EXISTS idx_applications_workspace ON applications(workspace_id)",

    # ── conversations ───────────────────────────────────────────────────────
    "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS workspace_id UUID",
    f"UPDATE conversations SET workspace_id = '{DEFAULT_WORKSPACE_ID}' WHERE workspace_id IS NULL",
    "CREATE INDEX IF NOT EXISTS idx_conversations_workspace ON conversations(workspace_id)",

    # ── messages ────────────────────────────────────────────────────────────
    "ALTER TABLE messages ADD COLUMN IF NOT EXISTS workspace_id UUID",
    f"UPDATE messages SET workspace_id = '{DEFAULT_WORKSPACE_ID}' WHERE workspace_id IS NULL",
    "CREATE INDEX IF NOT EXISTS idx_messages_workspace ON messages(workspace_id)",

    # ── workflow_nodes（透過 application 推導，但維持自身 workspace_id 以利直接查詢）──
    "ALTER TABLE workflow_nodes ADD COLUMN IF NOT EXISTS workspace_id UUID",
    f"UPDATE workflow_nodes SET workspace_id = '{DEFAULT_WORKSPACE_ID}' WHERE workspace_id IS NULL",
    "CREATE INDEX IF NOT EXISTS idx_workflow_nodes_workspace ON workflow_nodes(workspace_id)",

    # ── workflow_edges ──────────────────────────────────────────────────────
    "ALTER TABLE workflow_edges ADD COLUMN IF NOT EXISTS workspace_id UUID",
    f"UPDATE workflow_edges SET workspace_id = '{DEFAULT_WORKSPACE_ID}' WHERE workspace_id IS NULL",
    "CREATE INDEX IF NOT EXISTS idx_workflow_edges_workspace ON workflow_edges(workspace_id)",

    # ── api_keys ────────────────────────────────────────────────────────────
    "ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS workspace_id UUID",
    f"UPDATE api_keys SET workspace_id = '{DEFAULT_WORKSPACE_ID}' WHERE workspace_id IS NULL",
    "CREATE INDEX IF NOT EXISTS idx_api_keys_workspace ON api_keys(workspace_id)",
]


async def run_bootstrap_ddl() -> None:
    engine = create_async_engine(settings.DB_URL, pool_size=1, max_overflow=0)
    try:
        for i, stmt in enumerate(_BOOTSTRAP_STATEMENTS, 1):
            try:
                async with engine.begin() as conn:
                    await conn.execute(text(stmt))
                log.info("agent_bootstrap_ddl_ok", step=i)
            except Exception as e:
                log.warning("agent_bootstrap_ddl_failed", step=i, error=str(e))
        log.info("agent_bootstrap_ddl_done")
    finally:
        await engine.dispose()
