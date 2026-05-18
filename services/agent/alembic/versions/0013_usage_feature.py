"""model_usage_logs.feature — v3.7 P2

Revision ID: 0013_usage_feature
Revises: 0012_conversation_cost
"""
from alembic import op

revision = "0013_usage_feature"
down_revision = "0012_conversation_cost"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE model_usage_logs
            ADD COLUMN IF NOT EXISTS feature VARCHAR(16);
        CREATE INDEX IF NOT EXISTS idx_mul_feature ON model_usage_logs(feature)
            WHERE feature IS NOT NULL;
    """)


def downgrade():
    op.execute("""
        DROP INDEX IF EXISTS idx_mul_feature;
        ALTER TABLE model_usage_logs DROP COLUMN IF EXISTS feature;
    """)
