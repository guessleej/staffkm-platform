"""user_quotas — v3.3 D1

Revision ID: 0004_user_quotas
Revises: 0003_trigger_run_cost
"""
from alembic import op

revision = "0004_user_quotas"
down_revision = "0003_trigger_run_cost"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_quotas (
            workspace_id          UUID NOT NULL,
            user_id               UUID NOT NULL,
            monthly_token_cap     BIGINT,
            monthly_cost_cap_usd  NUMERIC(12, 2),
            updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_by            UUID,
            PRIMARY KEY (workspace_id, user_id)
        );
        CREATE INDEX IF NOT EXISTS idx_user_quotas_ws ON user_quotas(workspace_id);
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS user_quotas")
