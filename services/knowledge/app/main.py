"""Knowledge Service — 知識庫管理服務"""
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
from app.api import documents, knowledge_bases, paragraphs, search, hit_test, tasks
from staffkm_core.utils.database import init_db

log = structlog.get_logger()


# Idempotent DDL — 啟動時補丁式遷移；asyncpg 一次只執行單一 statement，故拆成清單
_BOOTSTRAP_STATEMENTS: list[str] = [
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
]


async def _ensure_embedding_dimension(engine):
    """偵測並對齊 paragraph_embeddings.embedding 的維度，需與 settings.EMBEDDING_DIMENSION 一致。
    若有資料則跳過（避免破壞），請手動處理；若無資料則自動重建欄位與索引。"""
    async with engine.begin() as conn:
        # 查目前維度（atttypmod 對 vector 是 dim+4，所以實際維度是 atttypmod）
        result = await conn.execute(text(
            "SELECT atttypmod FROM pg_attribute "
            "WHERE attrelid='paragraph_embeddings'::regclass AND attname='embedding'"
        ))
        current_dim = (result.scalar_one_or_none() or 0)
        target_dim = settings.EMBEDDING_DIMENSION
        if current_dim == target_dim:
            log.info("embedding_dimension_ok", dim=current_dim)
            return
        # 不對齊 → 看是否有資料
        result = await conn.execute(text("SELECT count(*) FROM paragraph_embeddings"))
        count = result.scalar_one()
        if count > 0:
            log.error(
                "embedding_dimension_mismatch_has_data",
                current=current_dim, target=target_dim, rows=count,
                message="請手動 TRUNCATE paragraph_embeddings 後重新處理所有文件",
            )
            return
        # 無資料 — 安全重建
        log.warning("embedding_dimension_rebuilding", current=current_dim, target=target_dim)
        await conn.execute(text("DROP INDEX IF EXISTS idx_para_embed_vector"))
        await conn.execute(text(
            f"ALTER TABLE paragraph_embeddings "
            f"ALTER COLUMN embedding TYPE vector({target_dim})"
        ))
        await conn.execute(text(
            "CREATE INDEX idx_para_embed_vector ON paragraph_embeddings "
            "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
        ))
        log.info("embedding_dimension_rebuilt", dim=target_dim)


async def _run_bootstrap_ddl():
    engine = create_async_engine(settings.DB_URL, pool_size=1, max_overflow=0)
    try:
        for i, stmt in enumerate(_BOOTSTRAP_STATEMENTS, 1):
            try:
                async with engine.begin() as conn:
                    await conn.execute(text(stmt))
                log.info("bootstrap_ddl_step_ok", step=i)
            except Exception as e:
                log.warning("bootstrap_ddl_step_failed", step=i, error=str(e))
        try:
            await _ensure_embedding_dimension(engine)
        except Exception as e:
            log.warning("ensure_embedding_dimension_failed", error=str(e))
        log.info("bootstrap_ddl_done")
    finally:
        await engine.dispose()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(settings.DB_URL)
    await _run_bootstrap_ddl()
    log.info("knowledge_service_ready")
    yield


app = FastAPI(
    title="StaffKM Knowledge Service",
    description="知識庫管理服務 — 文件處理、向量化、語意檢索",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(knowledge_bases.router, prefix="/api/v1/knowledge/bases", tags=["知識庫"])
app.include_router(documents.router, prefix="/api/v1/knowledge/documents", tags=["文件管理"])
app.include_router(paragraphs.router, prefix="/api/v1/knowledge/paragraphs", tags=["段落管理"])
app.include_router(search.router, prefix="/api/v1/knowledge/search", tags=["語意檢索"])
app.include_router(hit_test.router, prefix="/api/v1/knowledge/hit-test", tags=["命中測試"])
app.include_router(tasks.router, prefix="/api/v1/knowledge/tasks", tags=["任務管理"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "knowledge"}
