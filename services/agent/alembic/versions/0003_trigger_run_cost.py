"""trigger run cost — v3.3 A4

Revision ID: 0003_trigger_run_cost
Revises: 0002_ai_models_pricing
Create Date: 2026-05-18
"""
from alembic import op

revision = "0003_trigger_run_cost"
down_revision = "0002_ai_models_pricing"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE event_trigger_runs
            ADD COLUMN IF NOT EXISTS tokens_used BIGINT NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS cost_usd    NUMERIC(12, 6) NOT NULL DEFAULT 0
    """)


def downgrade():
    op.execute("""
        ALTER TABLE event_trigger_runs
            DROP COLUMN IF EXISTS tokens_used,
            DROP COLUMN IF EXISTS cost_usd
    """)
