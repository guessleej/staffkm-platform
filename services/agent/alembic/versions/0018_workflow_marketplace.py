"""workflow marketplace public metadata — v4.10 J

Revision ID: 0018_workflow_marketplace
Revises: 0017_billing_tables
"""
from alembic import op

revision = "0018_workflow_marketplace"
down_revision = "0017_billing_tables"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE workspace_app_templates
            ADD COLUMN IF NOT EXISTS publisher_name      VARCHAR(64),
            ADD COLUMN IF NOT EXISTS publisher_url       TEXT,
            ADD COLUMN IF NOT EXISTS cover_image_url     TEXT,
            ADD COLUMN IF NOT EXISTS category            VARCHAR(32),
            ADD COLUMN IF NOT EXISTS tags                JSONB DEFAULT '[]'::jsonb,
            ADD COLUMN IF NOT EXISTS license             VARCHAR(32) DEFAULT 'MIT',
            ADD COLUMN IF NOT EXISTS verified            BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS rating_avg          NUMERIC(3, 2),
            ADD COLUMN IF NOT EXISTS rating_count        INT NOT NULL DEFAULT 0;
        CREATE INDEX IF NOT EXISTS idx_template_public_install
            ON workspace_app_templates(is_public, install_count DESC)
            WHERE is_public = TRUE;
        CREATE INDEX IF NOT EXISTS idx_template_category
            ON workspace_app_templates(category, install_count DESC)
            WHERE is_public = TRUE;

        -- rating 表
        CREATE TABLE IF NOT EXISTS template_ratings (
            template_id   UUID NOT NULL,
            user_id       UUID NOT NULL,
            rating        SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
            comment       TEXT,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (template_id, user_id)
        );
        CREATE INDEX IF NOT EXISTS idx_rating_template ON template_ratings(template_id, created_at DESC);
    """)


def downgrade():
    op.execute("""
        DROP TABLE IF EXISTS template_ratings;
        DROP INDEX IF EXISTS idx_template_category;
        DROP INDEX IF EXISTS idx_template_public_install;
        ALTER TABLE workspace_app_templates
            DROP COLUMN IF EXISTS publisher_name,
            DROP COLUMN IF EXISTS publisher_url,
            DROP COLUMN IF EXISTS cover_image_url,
            DROP COLUMN IF EXISTS category,
            DROP COLUMN IF EXISTS tags,
            DROP COLUMN IF EXISTS license,
            DROP COLUMN IF EXISTS verified,
            DROP COLUMN IF EXISTS rating_avg,
            DROP COLUMN IF EXISTS rating_count;
    """)
