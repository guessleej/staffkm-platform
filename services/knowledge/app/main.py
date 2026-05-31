"""Knowledge Service — 知識庫管理服務"""
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
from app.utils.migrate import run_alembic_upgrade
from app.api import documents, knowledge_bases, paragraphs, search, hit_test, tasks, folders, kb_grants, inline_write, web_sync, embedding_admin
from staffkm_core.utils import database as _db
from staffkm_core.utils.database import init_db
from staffkm_core.observability import setup_otel, instrument_fastapi
from staffkm_tenant import TenantContextMiddleware

log = structlog.get_logger()


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


async def _run_embedding_dimension_check():
    """v4.0：runtime safety — 對齊 settings.EMBEDDING_DIMENSION 跟實際 column 維度。
    不屬 schema 變更（取決 runtime config），故不放 alembic。"""
    engine = create_async_engine(settings.DB_URL, pool_size=1, max_overflow=0)
    try:
        await _ensure_embedding_dimension(engine)
    except Exception as e:
        log.warning("ensure_embedding_dimension_failed", error=str(e))
    finally:
        await engine.dispose()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_otel(service_name="staffkm-knowledge")
    init_db(settings.DB_URL)
    await run_alembic_upgrade()
    await _run_embedding_dimension_check()
    # v5.12: 內建 reranker 若啟用 → 啟動就 warmup 預載（避免第一次查詢慢）。失敗不阻斷。
    #   防呆：先判容器記憶體上限，不足就跳過 warmup 並給明確 error log（reranker 載入 ~1.9GB，
    #   上限 <~2.3GB 會 OOM-SIGKILL 整個行程 → 無限重啟，看似「知識庫全掛」）。
    if settings.RERANKER_DEFAULT_LOCAL:
        from app.core.local_reranker import memory_guard, warmup
        ok_mem, detail = memory_guard()
        if not ok_mem:
            log.error(
                "local_reranker_warmup_skipped_low_memory",
                reason=detail,
                hint="raise knowledge container memory to >=3g, or set RERANKER_DEFAULT_LOCAL=false",
            )
        else:
            try:
                import anyio
                ok = await anyio.to_thread.run_sync(warmup)
                log.info("local_reranker_warmup", loaded=ok, memory=detail)
            except Exception as e:  # noqa: BLE001
                log.warning("local_reranker_warmup_failed", error=str(e)[:200])
    log.info("knowledge_service_ready")
    yield


class GatewayHeadersMiddleware(BaseHTTPMiddleware):
    """從 Gateway 注入的 X-User-ID 標頭恢復 request.state（供 tenant middleware 取用）。"""
    async def dispatch(self, request: Request, call_next):
        request.state.user_id = request.headers.get("X-User-ID") or None
        request.state.roles   = [r for r in request.headers.get("X-User-Roles", "").split(",") if r]
        return await call_next(request)


def _user_id_from_request(req: Request) -> uuid.UUID | None:
    raw = getattr(req.state, "user_id", None) or req.headers.get("X-User-ID")
    if not raw:
        return None
    try:
        return uuid.UUID(raw)
    except (TypeError, ValueError):
        return None


app = FastAPI(
    title="StaffKM Knowledge Service",
    description="知識庫管理服務 — 文件處理、向量化、語意檢索",
    version="2.0.0",
    lifespan=lifespan,
)
instrument_fastapi(app, service_name="staffkm-knowledge")

# ── Middleware（starlette 規則：後加 = 外層 = 先跑）──────────────────
# 期望執行順序（request 進來時）：
#   GatewayHeaders → TenantContext → endpoint
# v4.0 P2: LegacyURLBridge 已移除（v3.1 sunset → v3.6 default 410 → v4.0 拔；knowledge service 同步於 v5.0.x 對齊）
# Prometheus /metrics — v2.2
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
# Tenant 必須在 GatewayHeaders 後跑，才能拿到 user_id
app.add_middleware(
    TenantContextMiddleware,
    session_factory=lambda: _db._session_factory,
    user_id_getter=_user_id_from_request,
)
app.add_middleware(GatewayHeadersMiddleware)

# ── Routes（v2：workspace-scoped）─────────────────────────────────────
_PREFIX = "/api/v1/workspace/{workspace_id}/knowledge"
app.include_router(knowledge_bases.router, prefix=f"{_PREFIX}/bases",      tags=["知識庫"])
app.include_router(folders.router,         prefix=f"{_PREFIX}/folders",    tags=["知識庫資料夾"])
app.include_router(documents.router,       prefix=f"{_PREFIX}/documents",  tags=["文件管理"])
app.include_router(paragraphs.router,      prefix=f"{_PREFIX}/paragraphs", tags=["段落管理"])
app.include_router(search.router,          prefix=f"{_PREFIX}/search",     tags=["語意檢索"])
app.include_router(hit_test.router,        prefix=f"{_PREFIX}/hit-test",   tags=["命中測試"])
app.include_router(embedding_admin.router, prefix=f"{_PREFIX}/embedding",   tags=["Embedding 熱換"])
app.include_router(tasks.router,           prefix=f"{_PREFIX}/tasks",      tags=["任務管理"])
app.include_router(kb_grants.router,       prefix=f"{_PREFIX}/bases",      tags=["KB 資源授權（Round 10-4）"])
app.include_router(inline_write.router,    prefix=f"{_PREFIX}/documents",  tags=["Workflow KB inline-write（RFC-013）"])
app.include_router(web_sync.router,        prefix=f"{_PREFIX}/bases",      tags=["Web KB 同步（Sprint 16）"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "knowledge"}
