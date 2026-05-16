"""Model Provider Registry API（M3 啟動）。

只暴露 read-only 的 registry 給前端，方便建立 model_providers 紀錄時下拉選單。
provider 本身（含 api_key）的 CRUD 仍走既有 admin 介面/DB seed。
"""
from fastapi import APIRouter, Depends

from app.core.providers import list_providers
from staffkm_core.schemas.response import ApiResponse
from staffkm_tenant import TenantContext, require_member

router = APIRouter()


@router.get(
    "/registry",
    response_model=ApiResponse,
    summary="列出支援的 Model Provider 中繼資料（20+）",
)
async def get_registry(_ctx: TenantContext = Depends(require_member)):
    return ApiResponse(data=list_providers())
