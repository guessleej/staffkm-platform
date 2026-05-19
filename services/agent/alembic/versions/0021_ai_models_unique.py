"""ai_models UNIQUE (provider_id, model_name) + dedup

Revision ID: 0021_ai_models_unique
Revises: 0020_system_settings

v5.0.4 的 pricing_seed INSERT ... WHERE NOT EXISTS 在 lifespan 多 worker 啟動時
有 race condition，可能寫入同 (provider_id, model_name) 兩列（例 gpt-4o ×2）。

本 migration:
  1. 刪重複（保留 created_at 最早的列）
  2. 加 UNIQUE INDEX (provider_id, model_name)，後續 INSERT 改走 ON CONFLICT DO NOTHING。
"""
from alembic import op

revision = "0021_ai_models_unique"
down_revision = "0020_system_settings"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        -- 1. dedup：a 是「較新」的列、b 是「最早」的列；保留 b
        DELETE FROM ai_models a USING ai_models b
        WHERE a.provider_id = b.provider_id
          AND a.model_name  = b.model_name
          AND a.created_at  > b.created_at;

        -- 2. UNIQUE constraint（用 unique index 形式，方便配 ON CONFLICT）
        CREATE UNIQUE INDEX IF NOT EXISTS uq_ai_models_provider_model
            ON ai_models(provider_id, model_name);
    """)


def downgrade():
    op.execute("DROP INDEX IF EXISTS uq_ai_models_provider_model")
