"""ai_models pricing — v3.2 P1

Revision ID: 0002_ai_models_pricing
Revises: 0001_baseline
Create Date: 2026-05-18
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_ai_models_pricing"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE ai_models
            ADD COLUMN IF NOT EXISTS price_per_1k_input_usd  NUMERIC(10, 6),
            ADD COLUMN IF NOT EXISTS price_per_1k_output_usd NUMERIC(10, 6)
    """)


def downgrade():
    op.execute("""
        ALTER TABLE ai_models
            DROP COLUMN IF EXISTS price_per_1k_input_usd,
            DROP COLUMN IF EXISTS price_per_1k_output_usd
    """)
