"""conversation_id attribution + chat_messages cost — v3.7 P1

Revision ID: 0012_conversation_cost
Revises: 0011_idempotency_keys
"""
from alembic import op

revision = "0012_conversation_cost"
down_revision = "0011_idempotency_keys"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE model_usage_logs
            ADD COLUMN IF NOT EXISTS conversation_id UUID,
            ADD COLUMN IF NOT EXISTS message_id      UUID;
        CREATE INDEX IF NOT EXISTS idx_mul_conv ON model_usage_logs(conversation_id) WHERE conversation_id IS NOT NULL;
    """)


def downgrade():
    op.execute("""
        ALTER TABLE model_usage_logs
            DROP COLUMN IF EXISTS conversation_id,
            DROP COLUMN IF EXISTS message_id;
    """)
