"""slow_query_explains — v3.8 P4

Revision ID: 0014_slow_query_explains
Revises: 0013_usage_feature
"""
from alembic import op

revision = "0014_slow_query_explains"
down_revision = "0013_usage_feature"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS slow_query_explains (
            id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            captured_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            duration_ms  INT NOT NULL,
            sql_text     TEXT NOT NULL,
            sql_hash     VARCHAR(64) NOT NULL,
            explain_json JSONB,
            explain_error TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_sqe_recent ON slow_query_explains(captured_at DESC);
        CREATE INDEX IF NOT EXISTS idx_sqe_hash   ON slow_query_explains(sql_hash, captured_at DESC);
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS slow_query_explains")
