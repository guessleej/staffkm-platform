"""quota_alerts — v3.3 D2

Revision ID: 0005_quota_alerts
Revises: 0004_user_quotas
"""
from alembic import op

revision = "0005_quota_alerts"
down_revision = "0004_user_quotas"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS quota_alerts (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id    UUID NOT NULL,
            scope           VARCHAR(16) NOT NULL,
            threshold_pct   INT NOT NULL,
            channel         VARCHAR(16) NOT NULL,
            target          TEXT NOT NULL,
            enabled         BOOLEAN NOT NULL DEFAULT TRUE,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT chk_scope CHECK (scope IN ('workspace', 'user')),
            CONSTRAINT chk_channel CHECK (channel IN ('email', 'slack', 'webhook')),
            CONSTRAINT chk_threshold CHECK (threshold_pct BETWEEN 1 AND 100)
        );
        CREATE INDEX IF NOT EXISTS idx_quota_alerts_ws ON quota_alerts(workspace_id, enabled);

        CREATE TABLE IF NOT EXISTS quota_alert_fires (
            alert_id     UUID NOT NULL,
            month        DATE NOT NULL,
            fired_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (alert_id, month)
        );
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS quota_alert_fires; DROP TABLE IF EXISTS quota_alerts;")
