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

    # ── projects（RFC-006 Phase C-1：Project 抽象層後端落地）────────────
    """
    CREATE TABLE IF NOT EXISTS projects (
        id              UUID PRIMARY KEY,
        workspace_id    UUID NOT NULL,
        name            VARCHAR(128) NOT NULL,
        description     TEXT,
        emoji           VARCHAR(8),
        system_prompt   TEXT,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
        created_by      UUID,
        updated_by      UUID
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_projects_workspace ON projects(workspace_id)",

    # project_resources：(project_id, kind, resource_id) 三元組關聯
    # kind 限定 'kb' | 'app'，未來可擴 'tool' / 'skill' 等
    """
    CREATE TABLE IF NOT EXISTS project_resources (
        project_id   UUID NOT NULL,
        kind         VARCHAR(16) NOT NULL,
        resource_id  VARCHAR(64) NOT NULL,
        attached_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
        attached_by  UUID,
        PRIMARY KEY (project_id, kind, resource_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_project_resources_project ON project_resources(project_id)",
    "CREATE INDEX IF NOT EXISTS idx_project_resources_kind ON project_resources(kind, resource_id)",

    # ── tools（RFC-006 新 backlog：對標 MaxKB 工具模組）─────────────────
    """
    CREATE TABLE IF NOT EXISTS tools (
        id              UUID PRIMARY KEY,
        workspace_id    UUID NOT NULL,
        name            VARCHAR(128) NOT NULL,
        description     TEXT,
        kind            VARCHAR(32) NOT NULL DEFAULT 'http',
        config          JSONB NOT NULL DEFAULT '{}',
        is_enabled      BOOLEAN NOT NULL DEFAULT TRUE,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
        created_by      UUID,
        updated_by      UUID
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_tools_workspace ON tools(workspace_id)",

    # ── skills（可重用 prompt 技能）─────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS skills (
        id              UUID PRIMARY KEY,
        workspace_id    UUID NOT NULL,
        name            VARCHAR(128) NOT NULL,
        description     TEXT,
        prompt_template TEXT NOT NULL DEFAULT '',
        variables       JSONB NOT NULL DEFAULT '[]',
        tags            JSONB NOT NULL DEFAULT '[]',
        created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
        created_by      UUID,
        updated_by      UUID
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_skills_workspace ON skills(workspace_id)",

    # ── data_sources（DB / API 連接器）─────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS data_sources (
        id              UUID PRIMARY KEY,
        workspace_id    UUID NOT NULL,
        name            VARCHAR(128) NOT NULL,
        description     TEXT,
        kind            VARCHAR(32) NOT NULL DEFAULT 'postgres',
        config          JSONB NOT NULL DEFAULT '{}',
        is_enabled      BOOLEAN NOT NULL DEFAULT TRUE,
        last_synced_at  TIMESTAMPTZ,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
        created_by      UUID,
        updated_by      UUID
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_data_sources_workspace ON data_sources(workspace_id)",

    # ── D-2：Application 引用 Skill ─────────────────────────────────
    "ALTER TABLE applications ADD COLUMN IF NOT EXISTS skill_ids JSONB NOT NULL DEFAULT '[]'::jsonb",

    # ── D-5：Folder 通用化（app / tool / skill / data_source 共用）─────
    """
    CREATE TABLE IF NOT EXISTS entity_folders (
        id              UUID PRIMARY KEY,
        workspace_id    UUID NOT NULL,
        entity_kind     VARCHAR(32) NOT NULL,
        parent_id       UUID,
        name            VARCHAR(128) NOT NULL,
        sort_order      INTEGER NOT NULL DEFAULT 0,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
        created_by      UUID
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_entity_folders_ws_kind ON entity_folders(workspace_id, entity_kind)",
    "CREATE INDEX IF NOT EXISTS idx_entity_folders_parent ON entity_folders(parent_id)",
    "ALTER TABLE applications  ADD COLUMN IF NOT EXISTS folder_id UUID",
    "ALTER TABLE tools         ADD COLUMN IF NOT EXISTS folder_id UUID",
    "ALTER TABLE skills        ADD COLUMN IF NOT EXISTS folder_id UUID",
    "ALTER TABLE data_sources  ADD COLUMN IF NOT EXISTS folder_id UUID",
    "CREATE INDEX IF NOT EXISTS idx_applications_folder ON applications(folder_id)",
    "CREATE INDEX IF NOT EXISTS idx_tools_folder        ON tools(folder_id)",
    "CREATE INDEX IF NOT EXISTS idx_skills_folder       ON skills(folder_id)",
    "CREATE INDEX IF NOT EXISTS idx_data_sources_folder ON data_sources(folder_id)",

    # ── D-7：Application 版本控制（snapshot + rollback）─────────────
    """
    CREATE TABLE IF NOT EXISTS application_versions (
        id              UUID PRIMARY KEY,
        application_id  UUID NOT NULL,
        workspace_id    UUID NOT NULL,
        version_number  INTEGER NOT NULL,
        snapshot        JSONB NOT NULL,
        note            TEXT,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
        created_by      UUID
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_app_versions_app ON application_versions(application_id, version_number DESC)",
    "CREATE INDEX IF NOT EXISTS idx_app_versions_workspace ON application_versions(workspace_id)",

    # ── M2：Workflow 版本控制（snapshot + manager 策略）─────────────
    """
    CREATE TABLE IF NOT EXISTS workflow_versions (
        id              UUID PRIMARY KEY,
        application_id  UUID NOT NULL,
        workspace_id    UUID NOT NULL,
        version_number  INTEGER NOT NULL,
        nodes           JSONB NOT NULL DEFAULT '[]'::jsonb,
        edges           JSONB NOT NULL DEFAULT '[]'::jsonb,
        note            TEXT,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
        created_by      UUID
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_wf_versions_app ON workflow_versions(application_id, version_number DESC)",
    "CREATE INDEX IF NOT EXISTS idx_wf_versions_workspace ON workflow_versions(workspace_id)",
    # Application 加 workflow_manager 欄位（執行策略）
    "ALTER TABLE applications ADD COLUMN IF NOT EXISTS workflow_manager VARCHAR(16) NOT NULL DEFAULT 'simple'",
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
