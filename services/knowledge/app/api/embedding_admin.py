"""Embedding 熱換 admin 端點（系統級）：觸發全庫重嵌 + 查進度。

POST /knowledge/embedding/reindex {model_name}  → 排程背景重嵌（admin/writer）
GET  /knowledge/embedding/reindex               → 查進度（system_settings 'embedding.reindex'）
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session
from staffkm_tenant import TenantContext, require_member, require_writer

router = APIRouter()


class ReindexReq(BaseModel):
    model_name: str = Field(..., min_length=1, max_length=256)


@router.post("/reindex", response_model=ApiResponse)
async def trigger_reindex(
    body: ReindexReq,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    """全庫重嵌指定 embedding 模型（系統級；維度不符會遷移共用 vector 欄、期間搜尋退化）。"""
    # 若已在跑就不重複排程
    row = (await session.execute(
        text("SELECT value FROM system_settings WHERE key = 'embedding.reindex'")
    )).fetchone()
    if row and isinstance(row.value, dict) and row.value.get("status") == "running":
        return ApiResponse(message="已有重嵌進行中", data=row.value)
    from app.tasks.reindex_embeddings import reindex
    task = reindex.delay(body.model_name)
    return ApiResponse(
        message="已排程全庫重嵌（背景處理；重嵌期間請勿上傳新文件）",
        data={"task_id": task.id, "model": body.model_name},
    )


@router.get("/reindex", response_model=ApiResponse)
async def reindex_status(
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    """查重嵌進度 + 目前生效的 embedding 模型。"""
    rows = await session.execute(
        text("SELECT key, value FROM system_settings WHERE key IN ('embedding.reindex', 'embedding.active')")
    )
    data = {r["key"]: r["value"] for r in rows.mappings().all()}
    return ApiResponse(data={
        "progress": data.get("embedding.reindex") or {"status": "idle"},
        "active": data.get("embedding.active"),
    })
