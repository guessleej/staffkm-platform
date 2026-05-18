"""account tokens (email verify + password reset) — v4.6 F

Revision ID: 0016_account_tokens
Revises: 0015_trial_workspaces

加入 self-service 帳號流程需要的 token 欄位（同 PG instance、合進 agent
alembic chain，避免多 chain 散落）：

- email_verified_at: 完成 verify 後寫入
- verify_token / verify_token_exp: 24h 內有效（POST /verify-email/send 生成）
- reset_token  / reset_token_exp : 1h 內有效（POST /forgot-password 生成）
"""
from alembic import op

revision = "0016_account_tokens"
down_revision = "0015_trial_workspaces"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE users
            ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS verify_token      VARCHAR(128),
            ADD COLUMN IF NOT EXISTS verify_token_exp  TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS reset_token       VARCHAR(128),
            ADD COLUMN IF NOT EXISTS reset_token_exp   TIMESTAMPTZ;
        CREATE INDEX IF NOT EXISTS idx_users_verify_token
            ON users(verify_token) WHERE verify_token IS NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_users_reset_token
            ON users(reset_token) WHERE reset_token IS NOT NULL;
    """)


def downgrade():
    op.execute("""
        DROP INDEX IF EXISTS idx_users_verify_token;
        DROP INDEX IF EXISTS idx_users_reset_token;
        ALTER TABLE users
            DROP COLUMN IF EXISTS email_verified_at,
            DROP COLUMN IF EXISTS verify_token,
            DROP COLUMN IF EXISTS verify_token_exp,
            DROP COLUMN IF EXISTS reset_token,
            DROP COLUMN IF EXISTS reset_token_exp;
    """)
