"""KB Folder API — 知識庫資料夾階層（RFC-006 Phase C-3）。

支援多層 parent_id 樹狀結構，KB.folder_id 指向資料夾（NULL = 根目錄）。

權限：
  list / get / tree     require_member
  create / update / move require_writer
  delete                require_admin
"""
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session
from staffkm_tenant import TenantContext, require_admin, require_member, require_writer

router = APIRouter()


# ── Schemas ─────────────────────────────────────────────────────────────────


class FolderCreate(BaseModel):
    name:       str = Field(..., max_length=128)
    parent_id:  uuid.UUID | None = None
    sort_order: int = 0


class FolderUpdate(BaseModel):
    name:       str | None = Field(default=None, max_length=128)
    parent_id:  uuid.UUID | None = None
    sort_order: int | None = None


class FolderOut(BaseModel):
    id:           uuid.UUID
    workspace_id: uuid.UUID
    parent_id:    uuid.UUID | None
    name:         str
    sort_order:   int
    kb_count:     int = 0
    created_at:   datetime
    updated_at:   datetime


class FolderTreeNode(FolderOut):
    children: list["FolderTreeNode"] = []


FolderTreeNode.model_rebuild()


# ── 列表（flat）─────────────────────────────────────────────────────────────


@router.get("", response_model=ApiResponse[list[FolderOut]], summary="列出所有資料夾（flat）")
async def list_folders(
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    # 順帶聚合每個 folder 內的 KB 數量
    rows = await session.execute(
        text(
            """
            SELECT f.*, COALESCE(c.cnt, 0) AS kb_count
            FROM kb_folders f
            LEFT JOIN (
                SELECT folder_id, COUNT(*) AS cnt
                FROM knowledge_bases
                WHERE workspace_id = :ws
                GROUP BY folder_id
            ) c ON c.folder_id = f.id
            WHERE f.workspace_id = :ws
            ORDER BY f.sort_order, f.created_at
            """
        ),
        {"ws": str(ctx.workspace_id)},
    )
    items = [dict(r._mapping) for r in rows.fetchall()]
    return ApiResponse(data=[FolderOut(**x) for x in items])


# ── 樹狀 ────────────────────────────────────────────────────────────────────


@router.get("/tree", response_model=ApiResponse[list[FolderTreeNode]], summary="取得資料夾樹狀結構")
async def folder_tree(
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    rows = await session.execute(
        text(
            """
            SELECT f.*, COALESCE(c.cnt, 0) AS kb_count
            FROM kb_folders f
            LEFT JOIN (
                SELECT folder_id, COUNT(*) AS cnt
                FROM knowledge_bases
                WHERE workspace_id = :ws
                GROUP BY folder_id
            ) c ON c.folder_id = f.id
            WHERE f.workspace_id = :ws
            ORDER BY f.sort_order, f.created_at
            """
        ),
        {"ws": str(ctx.workspace_id)},
    )
    flat = [FolderTreeNode(**dict(r._mapping), children=[]) for r in rows.fetchall()]
    by_id: dict[uuid.UUID, FolderTreeNode] = {f.id: f for f in flat}
    roots: list[FolderTreeNode] = []
    for f in flat:
        if f.parent_id and f.parent_id in by_id:
            by_id[f.parent_id].children.append(f)
        else:
            roots.append(f)
    return ApiResponse(data=roots)


# ── 建立 ────────────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=ApiResponse[FolderOut],
    status_code=status.HTTP_201_CREATED,
    summary="建立資料夾（writer）",
)
async def create_folder(
    body: FolderCreate,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    # 若帶 parent_id，確認 parent 屬於同 workspace
    if body.parent_id:
        chk = await session.execute(
            text("SELECT id FROM kb_folders WHERE id = :id AND workspace_id = :ws"),
            {"id": str(body.parent_id), "ws": str(ctx.workspace_id)},
        )
        if not chk.fetchone():
            raise HTTPException(status_code=400, detail="parent_id 不存在")

    new_id = uuid.uuid4()
    now = datetime.utcnow()
    await session.execute(
        text(
            """
            INSERT INTO kb_folders (
                id, workspace_id, parent_id, name, sort_order,
                created_at, updated_at, created_by
            ) VALUES (
                :id, :ws, :pid, :name, :sort, :now, :now, :by
            )
            """
        ),
        {
            "id": str(new_id),
            "ws": str(ctx.workspace_id),
            "pid": str(body.parent_id) if body.parent_id else None,
            "name": body.name,
            "sort": body.sort_order,
            "now": now,
            "by": str(ctx.user_id),
        },
    )
    row = await session.execute(
        text("SELECT *, 0 AS kb_count FROM kb_folders WHERE id = :id"),
        {"id": str(new_id)},
    )
    return ApiResponse(data=FolderOut(**dict(row.fetchone()._mapping)))


# ── 更新 ────────────────────────────────────────────────────────────────────


@router.put("/{folder_id}", response_model=ApiResponse[FolderOut], summary="更新資料夾")
async def update_folder(
    folder_id: uuid.UUID,
    body: FolderUpdate,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    chk = await session.execute(
        text("SELECT id FROM kb_folders WHERE id = :id AND workspace_id = :ws"),
        {"id": str(folder_id), "ws": str(ctx.workspace_id)},
    )
    if not chk.fetchone():
        raise HTTPException(status_code=404, detail="資料夾不存在")

    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=422, detail="未提供任何更新欄位")

    # 防環：parent_id 不能是自己
    if "parent_id" in updates and updates["parent_id"] is not None:
        if str(updates["parent_id"]) == str(folder_id):
            raise HTTPException(status_code=400, detail="parent 不能是自己")

    set_parts: list[str] = ["updated_at = :now"]
    params: dict[str, Any] = {"id": str(folder_id), "ws": str(ctx.workspace_id), "now": datetime.utcnow()}
    for k, v in updates.items():
        if k == "parent_id":
            set_parts.append("parent_id = :parent_id")
            params["parent_id"] = str(v) if v else None
        else:
            set_parts.append(f"{k} = :{k}")
            params[k] = v

    await session.execute(
        text(
            f"UPDATE kb_folders SET {', '.join(set_parts)} "
            f"WHERE id = :id AND workspace_id = :ws"
        ),
        params,
    )
    row = await session.execute(
        text("SELECT *, 0 AS kb_count FROM kb_folders WHERE id = :id"),
        {"id": str(folder_id)},
    )
    return ApiResponse(data=FolderOut(**dict(row.fetchone()._mapping)))


# ── 刪除 ────────────────────────────────────────────────────────────────────


@router.delete("/{folder_id}", response_model=ApiResponse, summary="刪除資料夾（admin；其下 KB 變為根目錄）")
async def delete_folder(
    folder_id: uuid.UUID,
    ctx: TenantContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    chk = await session.execute(
        text("SELECT id FROM kb_folders WHERE id = :id AND workspace_id = :ws"),
        {"id": str(folder_id), "ws": str(ctx.workspace_id)},
    )
    if not chk.fetchone():
        raise HTTPException(status_code=404, detail="資料夾不存在")

    # 子資料夾與 KB 一律拉回根目錄（軟性處理，避免級聯刪除驚喜）
    await session.execute(
        text("UPDATE kb_folders SET parent_id = NULL WHERE parent_id = :id"),
        {"id": str(folder_id)},
    )
    await session.execute(
        text("UPDATE knowledge_bases SET folder_id = NULL WHERE folder_id = :id"),
        {"id": str(folder_id)},
    )
    await session.execute(
        text("DELETE FROM kb_folders WHERE id = :id AND workspace_id = :ws"),
        {"id": str(folder_id), "ws": str(ctx.workspace_id)},
    )
    return ApiResponse(message="資料夾已刪除，其下資源移至根目錄")
