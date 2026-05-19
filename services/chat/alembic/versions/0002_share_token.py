"""conversations: share_token (MaxKB v2.7 對齊)

Revision ID: 0002_share_token
Revises: 0001_baseline

讓 user 點「分享」產生 share_token；公開頁 `/share/{token}` 唯讀展示對話。
ALTER ... IF NOT EXISTS（idempotent，符合 CLAUDE.md §9）。
"""
from alembic import op

revision = "0002_share_token"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE conversations ADD COLUMN IF NOT EXISTS share_token TEXT;
        CREATE UNIQUE INDEX IF NOT EXISTS uq_conversations_share_token
            ON conversations(share_token) WHERE share_token IS NOT NULL;
    """)


def downgrade():
    op.execute("""
        DROP INDEX IF EXISTS uq_conversations_share_token;
        ALTER TABLE conversations DROP COLUMN IF EXISTS share_token;
    """)
