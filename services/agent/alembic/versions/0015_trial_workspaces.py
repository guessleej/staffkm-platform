"""trial workspaces — v4.1 A

Revision ID: 0015_trial_workspaces
Revises: 0014_slow_query_explains

加 trial / signup 相關欄位到 workspace 表（singular, 對齊既有 schema）。

- trial_expires_at: 14 天試用到期時間（NULL = 非 trial）
- trial_plan      : 'free-trial' / NULL；之後 v4.7 接 paid plan
- is_frozen       : 過期後 trial_expiry_worker 寫 TRUE，阻擋寫入
- signup_email    : 自助 signup 的原始 email（追溯用）
- signup_source   : self-service / sales-demo / admin-invite
"""
from alembic import op

revision = "0015_trial_workspaces"
down_revision = "0014_slow_query_explains"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE workspace
            ADD COLUMN IF NOT EXISTS trial_expires_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS trial_plan       VARCHAR(32),
            ADD COLUMN IF NOT EXISTS is_frozen        BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS signup_email     VARCHAR(256),
            ADD COLUMN IF NOT EXISTS signup_source    VARCHAR(32);
        CREATE INDEX IF NOT EXISTS idx_ws_trial_expiry ON workspace(trial_expires_at)
            WHERE trial_expires_at IS NOT NULL AND is_frozen = FALSE;
    """)


def downgrade():
    op.execute("""
        DROP INDEX IF EXISTS idx_ws_trial_expiry;
        ALTER TABLE workspace
            DROP COLUMN IF EXISTS trial_expires_at,
            DROP COLUMN IF EXISTS trial_plan,
            DROP COLUMN IF EXISTS is_frozen,
            DROP COLUMN IF EXISTS signup_email,
            DROP COLUMN IF EXISTS signup_source;
    """)
