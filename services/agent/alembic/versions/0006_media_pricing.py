"""media pricing + usage unit type — v3.4 P1

Revision ID: 0006_media_pricing
Revises: 0005_quota_alerts
"""
from alembic import op

revision = "0006_media_pricing"
down_revision = "0005_quota_alerts"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE ai_models
            ADD COLUMN IF NOT EXISTS price_per_image_usd      NUMERIC(10, 6),
            ADD COLUMN IF NOT EXISTS price_per_second_usd     NUMERIC(10, 6),
            ADD COLUMN IF NOT EXISTS price_per_1k_chars_usd   NUMERIC(10, 6),
            ADD COLUMN IF NOT EXISTS price_per_call_usd       NUMERIC(10, 6)
    """)
    op.execute("""
        ALTER TABLE model_usage_logs
            ADD COLUMN IF NOT EXISTS unit_type   VARCHAR(16),
            ADD COLUMN IF NOT EXISTS unit_count  NUMERIC(12, 4)
    """)


def downgrade():
    op.execute("""
        ALTER TABLE ai_models
            DROP COLUMN IF EXISTS price_per_image_usd,
            DROP COLUMN IF EXISTS price_per_second_usd,
            DROP COLUMN IF EXISTS price_per_1k_chars_usd,
            DROP COLUMN IF EXISTS price_per_call_usd
    """)
    op.execute("""
        ALTER TABLE model_usage_logs
            DROP COLUMN IF EXISTS unit_type,
            DROP COLUMN IF EXISTS unit_count
    """)
