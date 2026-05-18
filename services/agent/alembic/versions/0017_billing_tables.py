"""billing — Stripe + usage records — v4.7+v4.8 G+H

Revision ID: 0017_billing_tables
Revises: 0016_account_tokens
"""
from alembic import op

revision = "0017_billing_tables"
down_revision = "0016_account_tokens"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        -- workspace billing 帳戶（Stripe customer + plan info）
        CREATE TABLE IF NOT EXISTS billing_accounts (
            workspace_id      UUID PRIMARY KEY,
            stripe_customer_id VARCHAR(64),
            stripe_subscription_id VARCHAR(64),
            plan              VARCHAR(32) NOT NULL DEFAULT 'trial',
            status            VARCHAR(32) NOT NULL DEFAULT 'active',
            credits_balance   NUMERIC(12, 6) NOT NULL DEFAULT 0,
            billing_cycle_anchor TIMESTAMPTZ,
            current_period_start TIMESTAMPTZ,
            current_period_end   TIMESTAMPTZ,
            created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        -- 發票紀錄（Stripe webhook 寫入）
        CREATE TABLE IF NOT EXISTS billing_invoices (
            id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id      UUID NOT NULL,
            stripe_invoice_id VARCHAR(64) UNIQUE,
            amount_usd        NUMERIC(12, 2) NOT NULL,
            currency          VARCHAR(8) DEFAULT 'usd',
            status            VARCHAR(32) NOT NULL,
            period_start      TIMESTAMPTZ,
            period_end        TIMESTAMPTZ,
            invoice_pdf_url   TEXT,
            created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_inv_ws ON billing_invoices(workspace_id, created_at DESC);

        -- usage_reports：聚合送 stripe meter API 的紀錄（avoid 重送）
        CREATE TABLE IF NOT EXISTS usage_reports (
            id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id      UUID NOT NULL,
            period_start      TIMESTAMPTZ NOT NULL,
            period_end        TIMESTAMPTZ NOT NULL,
            tokens_reported   BIGINT NOT NULL DEFAULT 0,
            cost_reported_usd NUMERIC(12, 6) NOT NULL DEFAULT 0,
            stripe_event_id   VARCHAR(64),
            reported_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (workspace_id, period_start, period_end)
        );
        CREATE INDEX IF NOT EXISTS idx_ur_ws ON usage_reports(workspace_id, period_start DESC);

        -- credit ledger（pre-paid credits 流水）
        CREATE TABLE IF NOT EXISTS credit_ledger (
            id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id      UUID NOT NULL,
            delta_usd         NUMERIC(12, 6) NOT NULL,
            reason            VARCHAR(32) NOT NULL,
            reference         VARCHAR(128),
            balance_after     NUMERIC(12, 6) NOT NULL,
            created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_cl_ws ON credit_ledger(workspace_id, created_at DESC);
    """)


def downgrade():
    op.execute("""
        DROP TABLE IF EXISTS credit_ledger;
        DROP TABLE IF EXISTS usage_reports;
        DROP TABLE IF EXISTS billing_invoices;
        DROP TABLE IF EXISTS billing_accounts;
    """)
