"""Chat Service — 對話管理服務"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.api.conversations import router as conv_router
from staffkm_core.utils.database import init_db
from app.config import settings
from app.utils.migrate import run_alembic_upgrade

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(settings.DB_URL)
    await run_alembic_upgrade()
    log.info("chat_service_ready")
    yield


app = FastAPI(title="StaffKM Chat Service", version="1.0.0", lifespan=lifespan)
# Prometheus /metrics — v2.2
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(conv_router, prefix="/api/v1/chat/conversations", tags=["對話管理"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "chat"}
