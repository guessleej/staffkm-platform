"""Celery 任務狀態查詢 API（RFC-001 Stage 2 — 需 workspace 成員身份）"""
from fastapi import APIRouter, Depends
from celery.result import AsyncResult

from app.tasks.celery_app import celery_app
from staffkm_core.schemas.response import ApiResponse
from staffkm_tenant import TenantContext, require_admin, require_member

router = APIRouter()


@router.get("/{task_id}", response_model=ApiResponse)
async def get_task_status(
    task_id: str,
    ctx: TenantContext = Depends(require_member),
):
    result = AsyncResult(task_id, app=celery_app)
    data = {
        "task_id": task_id,
        "status": result.status,
        "result": None,
        "error": None,
    }
    if result.successful():
        data["result"] = result.result
    elif result.failed():
        data["error"] = str(result.result)
    return ApiResponse(data=data)


@router.post("/{task_id}/revoke", response_model=ApiResponse)
async def revoke_task(
    task_id: str,
    ctx: TenantContext = Depends(require_admin),
):
    celery_app.control.revoke(task_id, terminate=False)
    return ApiResponse(message="任務已標記取消（若尚未啟動）")
