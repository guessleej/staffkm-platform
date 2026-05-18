"""system_settings — v5.0.1 admin

Revision ID: 0020_system_settings
Revises: 0019_multi_region
"""
from alembic import op

revision = "0020_system_settings"
down_revision = "0019_multi_region"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS system_settings (
            key         VARCHAR(64) PRIMARY KEY,
            value       JSONB NOT NULL,
            description TEXT,
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_by  UUID
        );
        -- seed 預設值
        INSERT INTO system_settings (key, value, description) VALUES
          ('embedding.default_model',  '"bge-m3"',          'Default embedding model'),
          ('embedding.dimension',      '1024',               'Embedding vector dimension'),
          ('reranker.default_type',    '"cross_encoder"',    'Default reranker (cohere/ollama/cross_encoder/http)'),
          ('search.rrf_default_vector_weight', '0.7',         'Hybrid search vector weight (0-1)'),
          ('search.default_top_k',     '5',                  'Default top_k for retrieval'),
          ('upload.max_file_size_mb',  '50',                 'Max upload size (MB)'),
          ('upload.allowed_extensions','["pdf","docx","md","txt","csv","html"]', 'Allowed extensions'),
          ('security.password_min_length',  '8',             'Min password length'),
          ('security.login_lockout_threshold', '5',          'Failed login attempts before captcha'),
          ('security.session_timeout_minutes', '60',         'Session idle timeout (minutes)')
        ON CONFLICT (key) DO NOTHING;
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS system_settings")
