"""Media Provider Registry API（M4 啟動）。

GET /media-providers/registry — 列出支援的 image / tts / stt provider
"""
from fastapi import APIRouter

from app.core.media import MEDIA_PROVIDER_REGISTRY
from staffkm_core.schemas.response import ApiResponse

router = APIRouter()


@router.get("/registry", response_model=ApiResponse, summary="列出支援的 Media Provider")
async def get_registry():
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
