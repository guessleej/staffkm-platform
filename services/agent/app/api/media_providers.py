"""Media Provider Registry API（M4 啟動）。

GET /media-providers/registry — 列出支援的 image / tts / stt provider
"""
from fastapi import APIRouter, Depends

from app.core.media import MEDIA_PROVIDER_REGISTRY
from staffkm_core.schemas.response import ApiResponse
from staffkm_tenant import TenantContext, require_member

router = APIRouter()


@router.get("/registry", response_model=ApiResponse, summary="列出支援的 Media Provider")
async def get_registry(_ctx: TenantContext = Depends(require_member)):
    return ApiResponse(data=[
        {
            "type":               m.type,
            "label":              m.label,
            "capability":         m.capability,
            "default_base_url":   m.default_base_url,
            "recommended_models": m.recommended_models,
            "notes":              m.notes,
        }
        for m in MEDIA_PROVIDER_REGISTRY
    ])
