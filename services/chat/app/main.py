"""Chat Service — 對話管理服務"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.api.conversations import router as conv_router, public_router as conv_public_router
from staffkm_core.utils.database import init_db
from staffkm_core.observability import setup_otel, instrument_fastapi
from app.config import settings
from app.utils.migrate import run_alembic_upgrade

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_otel(service_name="staffkm-chat")
    init_db(settings.DB_URL)
    await run_alembic_upgrade()
    log.info("chat_service_ready")
    yield


app = FastAPI(title="StaffKM Chat Service", version="1.0.0", lifespan=lifespan)
instrument_fastapi(app, service_name="staffkm-chat")
# Prometheus /metrics — v2.2
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(conv_router, prefix="/api/v1/chat/conversations", tags=["對話管理"])
# v2.7：公開分享對話（無需 JWT）
app.include_router(conv_public_router, prefix="/api/v1/public/conversations", tags=["公開對話分享 (v2.7)"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "chat"}
