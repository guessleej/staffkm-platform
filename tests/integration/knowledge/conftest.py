"""knowledge service 整合測試 fixture（真 pgvector）。

需 `vector` extension（pgvector image 內建）。embedding 欄用 **vector(4)**：hybrid_search
的 SQL 與維度無關（`CAST(:emb AS vector)` 不帶 dim），4 維讓測試能手刻好懂的向量、
cosine 排序一眼可驗（production 是 1024，但召回邏輯與維度無關）。

沒設 STAFFKM_TEST_DB_URL 或沒裝重依賴 → 整個目錄自動 skip 且不 top-level import 重依賴。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_TEST_DB_URL = os.environ.get("STAFFKM_TEST_DB_URL")


def _deps() -> bool:
    try:
        import pytest_asyncio  # noqa: F401
        import sqlalchemy  # noqa: F401
        return True
    except ImportError:
        return False


if not _TEST_DB_URL or not _deps():
    collect_ignore_glob = ["test_*.py"]
else:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # tests/integration（for _harness）
    from _harness import add_service_paths, make_db_session_fixture, run_ddl

    add_service_paths("knowledge")

    # 最小 schema：只含 hybrid_search SQL 真正 touch 的欄位（對齊查詢；漂移由查詢失敗擋）。
    _DDL = """
    CREATE EXTENSION IF NOT EXISTS vector;
    CREATE EXTENSION IF NOT EXISTS pgcrypto;

    CREATE TABLE IF NOT EXISTS documents (
        id   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        name text
    );

    CREATE TABLE IF NOT EXISTS paragraphs (
        id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        document_id       uuid,
        knowledge_base_id uuid,
        content           text,
        title             text,
        meta              jsonb,
        order_index       integer DEFAULT 0,
        is_active         boolean NOT NULL DEFAULT true,
        search_vector     tsvector
    );

    CREATE TABLE IF NOT EXISTS paragraph_embeddings (
        id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        paragraph_id uuid NOT NULL REFERENCES paragraphs(id) ON DELETE CASCADE,
        kb_id        uuid NOT NULL,
        embedding    vector(4),
        created_at   timestamptz DEFAULT now(),
        CONSTRAINT uniq_para_embed UNIQUE (paragraph_id)
    );
    """

    async def _schema(engine):
        await run_ddl(engine, _DDL)

    # paragraph_embeddings 先 truncate（有 FK 到 paragraphs）→ CASCADE 一起清。
    db_session = make_db_session_fixture(
        _schema,
        truncate_tables=("paragraph_embeddings", "paragraphs", "documents"),
    )
