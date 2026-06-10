"""v5.13 LLM Wiki API — 從知識庫生成可瀏覽的百科。

POST /bases/{kb_id}/wiki/generate  → 排程背景生成（writer）
GET  /bases/{kb_id}/wiki           → 生成狀態 + 頁面目錄（member）
GET  /bases/{kb_id}/wiki/pages/{page_id} → 單頁內容（member）
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session
from staffkm_tenant import TenantContext, require_member, require_writer

router = APIRouter()


@router.post("/{kb_id}/wiki/generate", response_model=ApiResponse, summary="排程生成 LLM Wiki")
async def generate_wiki(
    kb_id: uuid.UUID,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    # 已在跑就不重複排程
    row = (await session.execute(
        text("SELECT value FROM system_settings WHERE key = :k"),
        {"k": f"wiki.{kb_id}"},
    )).scalar()
    if row and isinstance(row, dict) and row.get("status") == "running":
        return ApiResponse(message="已有 Wiki 生成進行中", data=row)

    from app.tasks.wiki_gen import generate_wiki as _task
    _task.delay(str(kb_id))
    return ApiResponse(message="已開始生成 Wiki（背景進行）", data={"status": "queued"})


@router.get("/{kb_id}/wiki", response_model=ApiResponse, summary="Wiki 狀態 + 頁面目錄")
async def get_wiki(
    kb_id: uuid.UUID,
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    status_row = (await session.execute(
        text("SELECT value FROM system_settings WHERE key = :k"),
        {"k": f"wiki.{kb_id}"},
    )).scalar()
    pages = (await session.execute(
        text("""SELECT id, title, document_id, order_index, is_index
                FROM kb_wiki_pages WHERE knowledge_base_id = CAST(:k AS uuid)
                ORDER BY is_index DESC, order_index"""),
        {"k": str(kb_id)},
    )).mappings().all()
    return ApiResponse(data={
        "status": status_row or {"status": "none"},
        "pages": [
            {"id": str(p["id"]), "title": p["title"],
             "document_id": str(p["document_id"]) if p["document_id"] else None,
             "is_index": bool(p["is_index"])}
            for p in pages
        ],
    })


@router.get("/{kb_id}/wiki/pages/{page_id}", response_model=ApiResponse, summary="單頁內容")
async def get_wiki_page(
    kb_id: uuid.UUID,
    page_id: uuid.UUID,
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    row = (await session.execute(
        text("""SELECT id, title, content, document_id, is_index FROM kb_wiki_pages
                WHERE id = CAST(:p AS uuid) AND knowledge_base_id = CAST(:k AS uuid)"""),
        {"p": str(page_id), "k": str(kb_id)},
    )).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Wiki 頁面不存在")
    return ApiResponse(data={
        "id": str(row["id"]), "title": row["title"], "content": row["content"],
        "document_id": str(row["document_id"]) if row["document_id"] else None,
        "is_index": bool(row["is_index"]),
    })
