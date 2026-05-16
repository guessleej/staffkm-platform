"""Model Provider Registry API（M3 啟動）。

只暴露 read-only 的 registry 給前端，方便建立 model_providers 紀錄時下拉選單。
metadata 本身是 workspace-agnostic 的靜態列表，不需要 require_member —
任何登入者（admin UI / SDK / CLI）都應該能讀。

provider 本身（含 api_key）的 CRUD 仍走既有 admin 介面/DB seed。
"""
from fastapi import APIRouter

from app.core.providers import list_providers
from staffkm_core.schemas.response import ApiResponse

router = APIRouter()


@router.get(
    "/registry",
    response_model=ApiResponse,
    summary="列出支援的 Model Provider 中繼資料（25+）",
)
async def get_registry():
    return ApiResponse(data=list_providers())
