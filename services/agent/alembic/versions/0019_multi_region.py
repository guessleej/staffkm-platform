"""multi-region scaffolding — v5.0 K

Revision ID: 0019_multi_region
Revises: 0018_workflow_marketplace

v5.0 Theme K: active-active multi-region (scaffolding only).
- workspace.primary_region: L1 region-pin (per-workspace primary region)
- regions: cluster-wide region registry (id / name / DSN / minio endpoint)
- region_conflict_log: append log for any logical-replication / CRDT merge
  conflict, with manual resolve workflow

Schema 是 **純 additive** — 既有 deploy 不會受影響；middleware 預設 disabled。
真實 active-active write 流量留 v5.x。
"""
from alembic import op

revision = "0019_multi_region"
down_revision = "0018_workflow_marketplace"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        -- L1: workspace 綁定 primary region
        ALTER TABLE workspace
            ADD COLUMN IF NOT EXISTS primary_region VARCHAR(32) DEFAULT 'default';

        -- Region registry (cluster-wide)
        CREATE TABLE IF NOT EXISTS regions (
            id              VARCHAR(32) PRIMARY KEY,
            name            VARCHAR(64) NOT NULL,
            db_url          TEXT,
            minio_endpoint  TEXT,
            is_active       BOOLEAN NOT NULL DEFAULT TRUE,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        -- Conflict log: 任何 logical replication / CRDT merge 偵測到衝突寫一筆
        CREATE TABLE IF NOT EXISTS region_conflict_log (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            detected_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
            entity_type     VARCHAR(32) NOT NULL,
            entity_id       VARCHAR(64) NOT NULL,
            region_a        VARCHAR(32) NOT NULL,
            region_b        VARCHAR(32) NOT NULL,
            value_a         JSONB,
            value_b         JSONB,
            resolution      VARCHAR(16) DEFAULT 'pending',
            resolved_value  JSONB,
            resolved_at     TIMESTAMPTZ
        );
        CREATE INDEX IF NOT EXISTS idx_conflict_recent
            ON region_conflict_log(detected_at DESC);
        CREATE INDEX IF NOT EXISTS idx_conflict_pending
            ON region_conflict_log(detected_at DESC)
            WHERE resolution = 'pending';
    """)


def downgrade():
    op.execute("""
        DROP INDEX IF EXISTS idx_conflict_pending;
        DROP INDEX IF EXISTS idx_conflict_recent;
        DROP TABLE IF EXISTS region_conflict_log;
        DROP TABLE IF EXISTS regions;
        ALTER TABLE workspace DROP COLUMN IF EXISTS primary_region;
    """)
