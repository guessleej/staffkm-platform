"""Agent Service — 多場景行政 AI 代理人服務"""
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import agents, chat_stream, applications, api_keys, workflows, public
from staffkm_core.utils.database import init_db
from app.config import settings

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(settings.DB_URL)
    log.info("agent_service_ready")
    yield


app = FastAPI(
    title="StaffKM Agent Service",
    description="多場景行政 AI 代理人服務",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(agents.router, prefix="/api/v1/agents", tags=["代理人管理"])
app.include_router(chat_stream.router, prefix="/api/v1/agents", tags=["串流對話"])
app.include_router(applications.router, prefix="/api/v1/applications", tags=["Application Builder"])
app.include_router(api_keys.router, prefix="/api/v1/api-keys", tags=["API Key 管理"])
app.include_router(workflows.router, prefix="/api/v1/applications", tags=["Workflow 引擎"])
app.include_router(public.router, prefix="/api/v1/public/applications", tags=["公開存取"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "agent"}
