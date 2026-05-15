from fastapi import APIRouter
import httpx
from app.config import settings

router = APIRouter()

SERVICES = {
    "knowledge": settings.KNOWLEDGE_SERVICE_URL,
    "agent": settings.AGENT_SERVICE_URL,
    "auth": settings.AUTH_SERVICE_URL,
    "integration": settings.INTEGRATION_SERVICE_URL,
    "chat": settings.CHAT_SERVICE_URL,
}


@router.get("/health", summary="Gateway 健康檢查")
async def health():
    return {"status": "ok", "service": "staffkm-gateway"}


@router.get("/health/services", summary="所有服務健康狀態")
async def services_health():
    results = {}
    async with httpx.AsyncClient(timeout=5.0) as client:
        for name, url in SERVICES.items():
            try:
                r = await client.get(f"{url}/health")
                results[name] = "ok" if r.status_code == 200 else "degraded"
            except Exception:
                results[name] = "unreachable"
    overall = "ok" if all(v == "ok" for v in results.values()) else "degraded"
    return {"status": overall, "services": results}
