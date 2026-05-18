"""Integration Service — LINE / Teams / ERP 整合服務"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.connectors.line_bot import router as line_router
from app.connectors.teams_bot import router as teams_router
from app.config import settings
from staffkm_core.observability import setup_otel, instrument_fastapi

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_otel(service_name="staffkm-integration")
    log.info("integration_service_ready")
    yield


app = FastAPI(title="StaffKM Integration Service", version="1.0.0", lifespan=lifespan)
instrument_fastapi(app, service_name="staffkm-integration")
# Prometheus /metrics — v2.2
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(line_router, prefix="/api/v1/integrations", tags=["LINE Bot"])
app.include_router(teams_router, prefix="/api/v1/integrations", tags=["Teams Bot"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "integration"}
