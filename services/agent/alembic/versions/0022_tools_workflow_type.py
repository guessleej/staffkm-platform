"""tools: workflow-type + AI code gen support (MaxKB v2.8 對齊)

Revision ID: 0022_tools_workflow_type
Revises: 0021_ai_models_unique

新欄位：
  - tool_type        TEXT  — 'http' | 'mcp' | 'shell' | 'custom' | 'workflow'
                            （沿用既有 kind 欄位，但語意擴張；保留 kind 不動，
                             改另加 tool_type 以避免破壞既有 row）
  - application_id   UUID  — 當 tool_type='workflow' 時指向 applications.id
  - input_schema     JSONB — function-calling 用的 JSON schema（args）
  - output_schema    JSONB — function-calling 回傳結構
  - code             TEXT  — Python `def run(...)` 函式原碼（custom / AI 生成）

所有 ALTER 都 IF NOT EXISTS（idempotent，符合 CLAUDE.md §9）。
"""
from alembic import op

revision = "0022_tools_workflow_type"
down_revision = "0021_ai_models_unique"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE tools ADD COLUMN IF NOT EXISTS tool_type      TEXT;
        ALTER TABLE tools ADD COLUMN IF NOT EXISTS application_id UUID;
        ALTER TABLE tools ADD COLUMN IF NOT EXISTS input_schema   JSONB DEFAULT '{}'::jsonb;
        ALTER TABLE tools ADD COLUMN IF NOT EXISTS output_schema  JSONB DEFAULT '{}'::jsonb;
        ALTER TABLE tools ADD COLUMN IF NOT EXISTS code           TEXT;

        -- 已有 row 補 tool_type = kind（向下相容）
        UPDATE tools SET tool_type = kind WHERE tool_type IS NULL;

        CREATE INDEX IF NOT EXISTS ix_tools_application_id
            ON tools(application_id) WHERE application_id IS NOT NULL;
    """)


def downgrade():
    op.execute("""
        DROP INDEX IF EXISTS ix_tools_application_id;
        ALTER TABLE tools DROP COLUMN IF EXISTS code;
        ALTER TABLE tools DROP COLUMN IF EXISTS output_schema;
        ALTER TABLE tools DROP COLUMN IF EXISTS input_schema;
        ALTER TABLE tools DROP COLUMN IF EXISTS application_id;
        ALTER TABLE tools DROP COLUMN IF EXISTS tool_type;
    """)
