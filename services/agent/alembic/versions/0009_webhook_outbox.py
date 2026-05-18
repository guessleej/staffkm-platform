"""webhook_outbox — v3.6 P1

Revision ID: 0009_webhook_outbox
Revises: 0008_workflow_approvals
"""
from alembic import op

revision = "0009_webhook_outbox"
down_revision = "0008_workflow_approvals"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS webhook_outbox (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id  UUID,
            url           TEXT NOT NULL,
            method        VARCHAR(8) NOT NULL DEFAULT 'POST',
            headers       JSONB,
            body          JSONB,
            status        VARCHAR(16) NOT NULL DEFAULT 'pending',
            attempts      INT NOT NULL DEFAULT 0,
            next_retry_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            last_error    TEXT,
            last_status_code INT,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            delivered_at  TIMESTAMPTZ,
            source_type   VARCHAR(32),
            source_id     UUID,
            CONSTRAINT chk_outbox_status CHECK (status IN ('pending','in_flight','delivered','failed'))
        );
        CREATE INDEX IF NOT EXISTS idx_outbox_due ON webhook_outbox(next_retry_at) WHERE status = 'pending';
        CREATE INDEX IF NOT EXISTS idx_outbox_ws  ON webhook_outbox(workspace_id, status);
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS webhook_outbox")
