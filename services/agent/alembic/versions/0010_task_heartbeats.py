"""task_heartbeats — v3.6 P2

Revision ID: 0010_task_heartbeats
Revises: 0009_webhook_outbox
"""
from alembic import op

revision = "0010_task_heartbeats"
down_revision = "0009_webhook_outbox"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS task_heartbeats (
            worker_name  VARCHAR(64) PRIMARY KEY,
            pid          INT,
            host         VARCHAR(128),
            started_at   TIMESTAMPTZ NOT NULL,
            last_beat    TIMESTAMPTZ NOT NULL,
            in_flight    INT NOT NULL DEFAULT 0
        );
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS task_heartbeats")
