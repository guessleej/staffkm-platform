"""GraphRAG 加法層 — 圖譜表 + graph_enabled 旗標 (RFC-014, MVP v5.11.0)

實體圖跑在 PG/pgvector（不引入 Neo4j）：
  - kb_entities          實體（含 embedding 供 query 比對；description 僅路由不當答案）
  - kb_entity_mentions   實體↔段落（FK CASCADE 隨段落清理；實體錨定召回的 JOIN 來源）
  - kb_relations         實體間有向邊（dedup on src+dst+type）
  - kb_relation_mentions 關係↔段落（Phase 2）
  - kb_communities       Louvain 社群 + 摘要（Phase 3）
  - knowledge_bases.graph_enabled  per-KB opt-in（預設 false → 零回歸）

全程 IF NOT EXISTS（idempotent，CLAUDE.md §9）。

Revision ID: 0003_graphrag
Revises: 0002_knowledge_schema_promoted
Create Date: 2026-05-22
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0003_graphrag"
down_revision: Union[str, None] = "0002_knowledge_schema_promoted"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_STATEMENTS: list[str] = [
    # per-KB opt-in 旗標
    "ALTER TABLE knowledge_bases ADD COLUMN IF NOT EXISTS graph_enabled boolean NOT NULL DEFAULT false",

    # 實體
    """CREATE TABLE IF NOT EXISTS kb_entities (
        id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        workspace_id      uuid NOT NULL,
        knowledge_base_id uuid NOT NULL,
        name              text NOT NULL,
        norm_name         text NOT NULL,
        aliases           jsonb NOT NULL DEFAULT '[]',
        entity_type       text NOT NULL DEFAULT 'concept',
        description       text,
        embedding         vector(1024),
        mention_count     int  NOT NULL DEFAULT 0,
        confidence        real NOT NULL DEFAULT 1.0,
        created_at        timestamptz NOT NULL DEFAULT now(),
        updated_at        timestamptz NOT NULL DEFAULT now()
    )""",
    "CREATE INDEX IF NOT EXISTS ix_kb_entities_kb ON kb_entities(knowledge_base_id)",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_kb_entities_norm ON kb_entities(knowledge_base_id, norm_name, entity_type)",
    "CREATE INDEX IF NOT EXISTS ix_kb_entities_vec ON kb_entities USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)",

    # 實體↔段落 mention（FK CASCADE）
    """CREATE TABLE IF NOT EXISTS kb_entity_mentions (
        entity_id    uuid NOT NULL REFERENCES kb_entities(id) ON DELETE CASCADE,
        paragraph_id uuid NOT NULL REFERENCES paragraphs(id)  ON DELETE CASCADE,
        workspace_id uuid NOT NULL,
        quote        text,
        PRIMARY KEY (entity_id, paragraph_id)
    )""",
    "CREATE INDEX IF NOT EXISTS ix_kb_mentions_para ON kb_entity_mentions(paragraph_id)",

    # 關係
    """CREATE TABLE IF NOT EXISTS kb_relations (
        id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        workspace_id      uuid NOT NULL,
        knowledge_base_id uuid NOT NULL,
        src_entity_id     uuid NOT NULL REFERENCES kb_entities(id) ON DELETE CASCADE,
        dst_entity_id     uuid NOT NULL REFERENCES kb_entities(id) ON DELETE CASCADE,
        relation_type     text NOT NULL,
        description       text,
        weight            real NOT NULL DEFAULT 1.0,
        confidence        real NOT NULL DEFAULT 1.0,
        created_at        timestamptz NOT NULL DEFAULT now()
    )""",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_kb_relations ON kb_relations(knowledge_base_id, src_entity_id, dst_entity_id, relation_type)",
    "CREATE INDEX IF NOT EXISTS ix_kb_relations_src ON kb_relations(src_entity_id)",
    "CREATE INDEX IF NOT EXISTS ix_kb_relations_dst ON kb_relations(dst_entity_id)",

    # 關係↔段落（Phase 2）
    """CREATE TABLE IF NOT EXISTS kb_relation_mentions (
        relation_id  uuid NOT NULL REFERENCES kb_relations(id) ON DELETE CASCADE,
        paragraph_id uuid NOT NULL REFERENCES paragraphs(id)   ON DELETE CASCADE,
        workspace_id uuid NOT NULL,
        PRIMARY KEY (relation_id, paragraph_id)
    )""",

    # 社群（Phase 3）
    """CREATE TABLE IF NOT EXISTS kb_communities (
        id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        workspace_id      uuid NOT NULL,
        knowledge_base_id uuid NOT NULL,
        level             int  NOT NULL DEFAULT 0,
        title             text,
        summary           text,
        entity_ids        jsonb NOT NULL DEFAULT '[]',
        cohesion_score    real,
        created_at        timestamptz NOT NULL DEFAULT now()
    )""",
    "CREATE INDEX IF NOT EXISTS ix_kb_communities_kb ON kb_communities(knowledge_base_id)",
]


def upgrade() -> None:
    for stmt in _STATEMENTS:
        op.execute(stmt)


def downgrade() -> None:
    for stmt in [
        "DROP TABLE IF EXISTS kb_relation_mentions",
        "DROP TABLE IF EXISTS kb_communities",
        "DROP TABLE IF EXISTS kb_relations",
        "DROP TABLE IF EXISTS kb_entity_mentions",
        "DROP TABLE IF EXISTS kb_entities",
        "ALTER TABLE knowledge_bases DROP COLUMN IF EXISTS graph_enabled",
    ]:
        op.execute(stmt)
