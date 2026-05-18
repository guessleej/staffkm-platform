"""knowledge schema promoted from bootstrap_ddl (v4.0-P1)

把 v3.1 之前在 services/knowledge/app/main.py `_BOOTSTRAP_STATEMENTS` 內所有
idempotent ALTER/CREATE/UPDATE 轉成 alembic revision，內容跟原 bootstrap 相同，
保留 IF NOT EXISTS 以兼容已執行過 bootstrap 的舊 deploy。

涵蓋：
  1. Hybrid Search tsvector + GIN index
  2. paragraph_embeddings UNIQUE(paragraph_id)
  3. 既有段落 search_vector 回填
  4. RFC-006 Phase C-3：kb_folders 階層 + knowledge_bases.folder_id
  5. RFC-006 切片技術升級：per-KB chunk_strategy / chunk_size / chunk_overlap
  6. Round 10-1：documents.tags / hit_strategy / is_enabled + indexes
  7. Round 10-2：Q&A 生成 (paragraphs.qa_pairs / documents.questions)
  8. Round 10-4：kb_grants（per-KB ACL）+ indexes
  9. Round 10-5 / RFC-013：Workflow KB (source_type / source_workflow_id)
  9b. Sprint 16：Web KB 同步 meta (source_url / last_synced_at / sync_status / sync_error)

Revision ID: 0002_knowledge_schema_promoted
Revises: 0001_baseline
Create Date: 2026-05-18
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0002_knowledge_schema_promoted"
down_revision: Union[str, None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_STATEMENTS: list[str] = [
    # 1. Hybrid Search 預計算 tsvector 欄位
    "ALTER TABLE paragraphs ADD COLUMN IF NOT EXISTS search_vector tsvector",
    "CREATE INDEX IF NOT EXISTS idx_paragraphs_search_vector "
    "ON paragraphs USING gin(search_vector)",

    # 2. paragraph_embeddings 的 UNIQUE(paragraph_id) — upsert 必要
    "DO $$ BEGIN "
    "  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uniq_para_embed') THEN "
    "    ALTER TABLE paragraph_embeddings ADD CONSTRAINT uniq_para_embed UNIQUE (paragraph_id); "
    "  END IF; "
    "END $$",

    # 3. 既有段落回填 search_vector（CJK 字符前後加空格再 tsvector）
    "UPDATE paragraphs "
    "SET search_vector = to_tsvector('simple', "
    "  regexp_replace(content, '([一-鿿㐀-䶿豈-﫿぀-ゟ゠-ヿ])', ' \\1 ', 'g')) "
    "WHERE search_vector IS NULL",

    # 4. RFC-006 Phase C-3：Folder 階層
    """
    CREATE TABLE IF NOT EXISTS kb_folders (
        id              UUID PRIMARY KEY,
        workspace_id    UUID NOT NULL,
        parent_id       UUID,
        name            VARCHAR(128) NOT NULL,
        sort_order      INTEGER NOT NULL DEFAULT 0,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
        created_by      UUID
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_kb_folders_workspace ON kb_folders(workspace_id)",
    "CREATE INDEX IF NOT EXISTS idx_kb_folders_parent ON kb_folders(parent_id)",
    "ALTER TABLE knowledge_bases ADD COLUMN IF NOT EXISTS folder_id UUID",
    "CREATE INDEX IF NOT EXISTS idx_kb_folder ON knowledge_bases(folder_id)",

    # 5. RFC-006 切片技術升級：per-KB 切片策略
    "ALTER TABLE knowledge_bases ADD COLUMN IF NOT EXISTS chunk_strategy VARCHAR(16) NOT NULL DEFAULT 'auto'",
    "ALTER TABLE knowledge_bases ADD COLUMN IF NOT EXISTS chunk_size INTEGER NOT NULL DEFAULT 512",
    "ALTER TABLE knowledge_bases ADD COLUMN IF NOT EXISTS chunk_overlap INTEGER NOT NULL DEFAULT 64",

    # 6. Round 10-1：文檔操作擴充
    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS tags JSONB NOT NULL DEFAULT '[]'::jsonb",
    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS hit_strategy VARCHAR(16) NOT NULL DEFAULT 'rag'",
    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS is_enabled BOOLEAN NOT NULL DEFAULT TRUE",
    "CREATE INDEX IF NOT EXISTS idx_documents_tags_gin ON documents USING gin (tags)",
    "CREATE INDEX IF NOT EXISTS idx_documents_kb_enabled ON documents (knowledge_base_id, is_enabled)",

    # 7. Round 10-2：Q&A 生成
    "ALTER TABLE paragraphs ADD COLUMN IF NOT EXISTS qa_pairs JSONB NOT NULL DEFAULT '[]'::jsonb",
    "ALTER TABLE documents ADD COLUMN IF NOT EXISTS questions JSONB NOT NULL DEFAULT '[]'::jsonb",

    # 9. Round 10-5 / RFC-013：Workflow KB
    "ALTER TABLE knowledge_bases ADD COLUMN IF NOT EXISTS source_type VARCHAR(16) NOT NULL DEFAULT 'manual'",
    "ALTER TABLE knowledge_bases ADD COLUMN IF NOT EXISTS source_workflow_id UUID",
    "CREATE INDEX IF NOT EXISTS idx_kb_source_workflow ON knowledge_bases(source_workflow_id) WHERE source_workflow_id IS NOT NULL",

    # 9b. Sprint 16：Web KB 同步 — source_url + crawl meta
    "ALTER TABLE knowledge_bases ADD COLUMN IF NOT EXISTS source_url TEXT",
    "ALTER TABLE knowledge_bases ADD COLUMN IF NOT EXISTS last_synced_at TIMESTAMPTZ",
    "ALTER TABLE knowledge_bases ADD COLUMN IF NOT EXISTS sync_status VARCHAR(16)",
    "ALTER TABLE knowledge_bases ADD COLUMN IF NOT EXISTS sync_error TEXT",

    # 8. Round 10-4：KB 資源授權（per-KB ACL）
    """
    CREATE TABLE IF NOT EXISTS kb_grants (
        id              UUID PRIMARY KEY,
        workspace_id    UUID NOT NULL,
        kb_id           UUID NOT NULL,
        principal_type  VARCHAR(16) NOT NULL,
        principal_id    VARCHAR(128) NOT NULL,
        access          VARCHAR(16) NOT NULL DEFAULT 'read',
        created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
        created_by      UUID,
        UNIQUE (kb_id, principal_type, principal_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_kb_grants_kb        ON kb_grants(kb_id)",
    "CREATE INDEX IF NOT EXISTS idx_kb_grants_ws        ON kb_grants(workspace_id)",
    "CREATE INDEX IF NOT EXISTS idx_kb_grants_principal ON kb_grants(principal_type, principal_id)",
]


def upgrade() -> None:
    for stmt in _STATEMENTS:
        op.execute(stmt)


def downgrade() -> None:
    # 不 drop — schema 退版會 break 已生產資料
    pass
