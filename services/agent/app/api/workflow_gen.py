"""Workflow generator API — v4.9 I.

POST /workflow-gen/generate — 自然語言 → workflow JSON 草稿
（前端可下載 / 套用到 LogicFlow 編輯器）。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.core.workflow_gen import generate_workflow
from staffkm_core.schemas.response import ApiResponse
from staffkm_tenant import TenantContext, require_member

router = APIRouter()


class GenerateRequest(BaseModel):
    user_request: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        description="自然語言描述你要的 workflow",
    )
    model: str | None = Field(
        default=None,
        description="覆寫 LLM model；預設用 workspace default",
    )


@router.post(
    "/generate",
    response_model=ApiResponse,
    summary="Generate workflow from natural language",
)
async def generate(
    body: GenerateRequest,
    ctx: TenantContext = Depends(require_member),
):
    # 用 workspace default LLM (簡化：用 settings.OPENAI_API_KEY 或 LLM_API_KEY)
    api_key = settings.OPENAI_API_KEY or settings.LLM_API_KEY
    base_url = (
        "https://api.openai.com/v1"
        if "openai" in settings.LLM_PROVIDER.lower()
        else settings.LLM_BASE_URL
    )
    model = body.model or settings.LLM_MODEL

    if not api_key:
        raise HTTPException(503, "LLM not configured (set OPENAI_API_KEY)")

    result = await generate_workflow(
        body.user_request,
        api_key=api_key,
        base_url=base_url,
        model=model,
    )

    return ApiResponse(data=result)
