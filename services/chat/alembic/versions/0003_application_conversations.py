"""conversations: application_id + scenario_id 放寬可空（統一對話 v5.10.14）

Revision ID: 0003_application_conversations
Revises: 0002_share_token

讓對話可綁 application（應用）而非僅 scenario（代理人）→ 應用「開始問答」
匯流進統一「對話」，消除獨立 ApplicationChatView。
ALTER ... IF NOT EXISTS / DROP NOT NULL（idempotent，符合 CLAUDE.md §9）。
"""
from alembic import op

revision = "0003_application_conversations"
down_revision = "0002_share_token"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE conversations ADD COLUMN IF NOT EXISTS application_id uuid;
        ALTER TABLE conversations ALTER COLUMN scenario_id DROP NOT NULL;
        CREATE INDEX IF NOT EXISTS ix_conversations_application_id
            ON conversations(application_id) WHERE application_id IS NOT NULL;
    """)


def downgrade():
    op.execute("""
        DROP INDEX IF EXISTS ix_conversations_application_id;
        ALTER TABLE conversations DROP COLUMN IF EXISTS application_id;
    """)
