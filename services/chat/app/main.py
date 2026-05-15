"""Chat Service — 對話管理服務"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.api.conversations import router as conv_router
from core.utils.database import init_db
from app.config import settings

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(settings.DB_URL)
    log.info("chat_service_ready")
    yield


app = FastAPI(title="StaffKM Chat Service", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(conv_router, prefix="/api/v1/chat/conversations", tags=["對話管理"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "chat"}
