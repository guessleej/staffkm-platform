"""workflow_run_steps — v3.5 P1

Revision ID: 0007_workflow_run_steps
Revises: 0006_media_pricing
"""
from alembic import op

revision = "0007_workflow_run_steps"
down_revision = "0006_media_pricing"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS workflow_run_steps (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            run_id          UUID NOT NULL,
            step_index      INT NOT NULL,
            node_key        VARCHAR(64) NOT NULL,
            node_type       VARCHAR(32) NOT NULL,
            status          VARCHAR(16) NOT NULL DEFAULT 'ok',
            input_snapshot  JSONB,
            output_snapshot JSONB,
            error           TEXT,
            attempts        INT NOT NULL DEFAULT 1,
            latency_ms      INT,
            started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            finished_at     TIMESTAMPTZ
        );
        CREATE INDEX IF NOT EXISTS idx_wrs_run ON workflow_run_steps(run_id, step_index);
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS workflow_run_steps")
