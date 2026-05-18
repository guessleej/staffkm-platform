"""idempotency_keys — v3.6 P3

Revision ID: 0011_idempotency_keys
Revises: 0010_task_heartbeats
"""
from alembic import op

revision = "0011_idempotency_keys"
down_revision = "0010_task_heartbeats"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS idempotency_keys (
            key            VARCHAR(128) NOT NULL,
            endpoint       VARCHAR(128) NOT NULL,
            workspace_id   UUID,
            response_json  JSONB,
            status_code    INT,
            created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
            expires_at     TIMESTAMPTZ NOT NULL DEFAULT (now() + interval '24 hours'),
            PRIMARY KEY (key, endpoint)
        );
        CREATE INDEX IF NOT EXISTS idx_idem_expire ON idempotency_keys(expires_at);
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS idempotency_keys")
