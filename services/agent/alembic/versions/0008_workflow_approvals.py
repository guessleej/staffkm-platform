"""workflow_approvals — v3.5 P2

Revision ID: 0008_workflow_approvals
Revises: 0007_workflow_run_steps
"""
from alembic import op

revision = "0008_workflow_approvals"
down_revision = "0007_workflow_run_steps"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS workflow_approvals (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            run_id        UUID NOT NULL,
            workspace_id  UUID NOT NULL,
            node_key      VARCHAR(64) NOT NULL,
            status        VARCHAR(16) NOT NULL DEFAULT 'pending',
            requester     VARCHAR(128),
            approver_id   UUID,
            approver_note TEXT,
            payload       JSONB,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            resolved_at   TIMESTAMPTZ,
            CONSTRAINT chk_approval_status CHECK (status IN ('pending','approved','rejected'))
        );
        CREATE INDEX IF NOT EXISTS idx_wa_run     ON workflow_approvals(run_id);
        CREATE INDEX IF NOT EXISTS idx_wa_pending ON workflow_approvals(workspace_id, status) WHERE status = 'pending';

        ALTER TABLE event_trigger_runs
            ADD COLUMN IF NOT EXISTS paused_at   TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS resumed_at  TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS resume_node VARCHAR(64);
    """)


def downgrade():
    op.execute("""
        ALTER TABLE event_trigger_runs
            DROP COLUMN IF EXISTS paused_at,
            DROP COLUMN IF EXISTS resumed_at,
            DROP COLUMN IF EXISTS resume_node;
        DROP TABLE IF EXISTS workflow_approvals;
    """)
