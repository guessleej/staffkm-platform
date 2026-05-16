"""Entity Folders — 通用 folder API（RFC-006 D-5）。

把 KB 的 folder 概念推到 Application / Tool / Skill / Data Source。
單一 entity_folders 表，靠 entity_kind 區分用途；前端帶 ?kind=app 取對應樹。

權限：member 看；writer 改；admin 刪。
刪除時：子資料夾與所屬 entity.folder_id 拉回根目錄（軟性處理）。
"""
import uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session
from staffkm_tenant import TenantContext, require_admin, require_member, require_writer

router = APIRouter()

EntityKind = Literal["app", "tool", "skill", "data_source"]
_KIND_TO_TABLE: dict[str, str] = {
    "app":         "applications",
    "tool":        "tools",
    "skill":       "skills",
    "data_source": "data_sources",
}


class FolderOut(BaseModel):
    id:           uuid.UUID
    workspace_id: uuid.UUID
    entity_kind:  str
    parent_id:    uuid.UUID | None
    name:         str
    sort_order:   int
    created_at:   datetime
    updated_at:   datetime


class FolderCreate(BaseModel):
    entity_kind: str = Field(..., max_length=32)
    parent_id:   uuid.UUID | None = None
    name:        str = Field(..., max_length=128)
    sort_order:  int = 0


class FolderUpdate(BaseModel):
    name:       str | None = Field(default=None, max_length=128)
    parent_id:  uuid.UUID | None = None
    sort_order: int | None = None


@router.get(
    "",
    response_model=ApiResponse[list[FolderOut]],
    summary="列出 entity_kind 對應的所有資料夾",
)
async def list_folders(
    kind: str = Query(..., description="app / tool / skill / data_source"),
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    if kind not in _KIND_TO_TABLE:
        raise HTTPException(status_code=400, detail=f"未支援的 kind：{kind}")
    rows = await session.execute(
        text(
            "SELECT * FROM entity_folders "
            "WHERE workspace_id = :ws AND entity_kind = :kind "
            "ORDER BY sort_order, created_at"
        ),
        {"ws": str(ctx.workspace_id), "kind": kind},
    )
    items = [FolderOut(**dict(r._mapping)) for r in rows.fetchall()]
    return ApiResponse(data=items)


@router.post(
    "",
    response_model=ApiResponse[FolderOut],
    status_code=status.HTTP_201_CREATED,
    summary="建立資料夾",
)
async def create_folder(
    body: FolderCreate,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    if body.entity_kind not in _KIND_TO_TABLE:
        raise HTTPException(status_code=400, detail=f"未支援的 kind：{body.entity_kind}")
    if body.parent_id:
        chk = await session.execute(
            text(
                "SELECT id FROM entity_folders "
                "WHERE id = :id AND workspace_id = :ws AND entity_kind = :kind"
            ),
            {"id": str(body.parent_id), "ws": str(ctx.workspace_id), "kind": body.entity_kind},
        )
        if not chk.fetchone():
            raise HTTPException(status_code=400, detail="parent_id 不存在於同 kind")

    new_id = uuid.uuid4()
    now = datetime.utcnow()
    await session.execute(
        text(
            """
            INSERT INTO entity_folders (
                id, workspace_id, entity_kind, parent_id, name, sort_order,
                created_at, updated_at, created_by
            ) VALUES (
                :id, :ws, :kind, :pid, :name, :sort, :now, :now, :by
            )
            """
        ),
        {
            "id": str(new_id), "ws": str(ctx.workspace_id),
            "kind": body.entity_kind,
            "pid": str(body.parent_id) if body.parent_id else None,
            "name": body.name, "sort": body.sort_order,
            "now": now, "by": str(ctx.user_id),
        },
    )
    row = await session.execute(
        text("SELECT * FROM entity_folders WHERE id = :id"), {"id": str(new_id)},
    )
    return ApiResponse(data=FolderOut(**dict(row.fetchone()._mapping)))


@router.put("/{folder_id}", response_model=ApiResponse[FolderOut], summary="更新資料夾")
async def update_folder(
    folder_id: uuid.UUID,
    body: FolderUpdate,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    chk = await session.execute(
        text("SELECT id FROM entity_folders WHERE id = :id AND workspace_id = :ws"),
        {"id": str(folder_id), "ws": str(ctx.workspace_id)},
    )
    if not chk.fetchone():
        raise HTTPException(status_code=404, detail="資料夾不存在")

    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=422, detail="未提供任何更新欄位")
    if "parent_id" in updates and updates["parent_id"] is not None:
        if str(updates["parent_id"]) == str(folder_id):
            raise HTTPException(status_code=400, detail="parent 不能是自己")

    set_parts = ["updated_at = :now"]
    params: dict[str, Any] = {"id": str(folder_id), "ws": str(ctx.workspace_id), "now": datetime.utcnow()}
    for k, v in updates.items():
        if k == "parent_id":
            set_parts.append("parent_id = :parent_id")
            params["parent_id"] = str(v) if v else None
        else:
            set_parts.append(f"{k} = :{k}")
            params[k] = v
    await session.execute(
        text(f"UPDATE entity_folders SET {', '.join(set_parts)} WHERE id = :id AND workspace_id = :ws"),
        params,
    )
    row = await session.execute(
        text("SELECT * FROM entity_folders WHERE id = :id"), {"id": str(folder_id)},
    )
    return ApiResponse(data=FolderOut(**dict(row.fetchone()._mapping)))


@router.delete("/{folder_id}", response_model=ApiResponse, summary="刪除資料夾（admin）")
async def delete_folder(
    folder_id: uuid.UUID,
    ctx: TenantContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    chk = await session.execute(
        text("SELECT id, entity_kind FROM entity_folders WHERE id = :id AND workspace_id = :ws"),
        {"id": str(folder_id), "ws": str(ctx.workspace_id)},
    )
    r = chk.fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="資料夾不存在")
    kind = dict(r._mapping)["entity_kind"]
    table = _KIND_TO_TABLE[kind]

    # 子資料夾、所屬 entity 都拉回根目錄
    await session.execute(
        text("UPDATE entity_folders SET parent_id = NULL WHERE parent_id = :id"),
        {"id": str(folder_id)},
    )
    await session.execute(
        text(f"UPDATE {table} SET folder_id = NULL WHERE folder_id = :id"),
        {"id": str(folder_id)},
    )
    await session.execute(
        text("DELETE FROM entity_folders WHERE id = :id AND workspace_id = :ws"),
        {"id": str(folder_id), "ws": str(ctx.workspace_id)},
    )
    return ApiResponse(message="資料夾已刪除，其下資源移至根目錄")
