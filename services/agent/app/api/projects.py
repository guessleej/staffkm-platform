"""Project API — workspace-scoped Project CRUD + 資源連動（RFC-006 C-1）。

權限：
  list / get                          require_member
  create / update / attach / detach   require_writer
  delete                              require_admin
"""
import json
import uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session
from staffkm_tenant import TenantContext, require_admin, require_member, require_writer

router = APIRouter()

ResourceKind = Literal["kb", "app"]


# ── Pydantic Schemas ────────────────────────────────────────────────────────


class ProjectCreate(BaseModel):
    name:          str = Field(..., max_length=128)
    description:   str | None = None
    emoji:         str | None = Field(default=None, max_length=8)
    system_prompt: str | None = None


class ProjectUpdate(BaseModel):
    name:          str | None = Field(default=None, max_length=128)
    description:   str | None = None
    emoji:         str | None = Field(default=None, max_length=8)
    system_prompt: str | None = None


class ProjectOut(BaseModel):
    id:                  uuid.UUID
    workspace_id:        uuid.UUID
    name:                str
    description:         str | None
    emoji:               str | None
    system_prompt:       str | None
    knowledge_base_ids:  list[str]
    application_ids:     list[str]
    created_at:          datetime
    updated_at:          datetime
    created_by:          uuid.UUID | None
    updated_by:          uuid.UUID | None


class AttachResource(BaseModel):
    kind:        ResourceKind
    resource_id: str = Field(..., max_length=64)


async def _hydrate_resources(
    session: AsyncSession, project_id: uuid.UUID
) -> tuple[list[str], list[str]]:
    """從 project_resources 表組出 (kb_ids, app_ids)。"""
    rows = await session.execute(
        text(
            "SELECT kind, resource_id FROM project_resources "
            "WHERE project_id = :pid"
        ),
        {"pid": str(project_id)},
    )
    kb_ids: list[str] = []
    app_ids: list[str] = []
    for r in rows.fetchall():
        d = dict(r._mapping)
        if d["kind"] == "kb":
            kb_ids.append(d["resource_id"])
        elif d["kind"] == "app":
            app_ids.append(d["resource_id"])
    return kb_ids, app_ids


async def _row_to_out(session: AsyncSession, row) -> ProjectOut:
    d = dict(row._mapping)
    kb_ids, app_ids = await _hydrate_resources(session, d["id"])
    return ProjectOut(
        **d,
        knowledge_base_ids=kb_ids,
        application_ids=app_ids,
    )


# ── 列表 ────────────────────────────────────────────────────────────────────


@router.get("", response_model=ApiResponse[list[ProjectOut]], summary="列出當前 workspace 的所有 Project")
async def list_projects(
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    rows = await session.execute(
        text(
            "SELECT * FROM projects "
            "WHERE workspace_id = :ws ORDER BY created_at DESC"
        ),
        {"ws": str(ctx.workspace_id)},
    )
    items = rows.fetchall()
    out = [await _row_to_out(session, r) for r in items]
    return ApiResponse(data=out)


# ── 建立 ────────────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=ApiResponse[ProjectOut],
    status_code=status.HTTP_201_CREATED,
    summary="建立 Project（writer 以上）",
)
async def create_project(
    body: ProjectCreate,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    new_id = uuid.uuid4()
    now = datetime.utcnow()
    await session.execute(
        text(
            """
            INSERT INTO projects (
                id, workspace_id, name, description, emoji, system_prompt,
                created_at, updated_at, created_by
            ) VALUES (
                :id, :ws, :name, :description, :emoji, :system_prompt,
                :now, :now, :by
            )
            """
        ),
        {
            "id": str(new_id),
            "ws": str(ctx.workspace_id),
            "name": body.name,
            "description": body.description,
            "emoji": body.emoji,
            "system_prompt": body.system_prompt,
            "now": now,
            "by": str(ctx.user_id),
        },
    )
    row = await session.execute(
        text("SELECT * FROM projects WHERE id = :id"), {"id": str(new_id)},
    )
    return ApiResponse(data=await _row_to_out(session, row.fetchone()))


# ── 取得單筆 ────────────────────────────────────────────────────────────────


@router.get("/{project_id}", response_model=ApiResponse[ProjectOut], summary="取得 Project 詳情")
async def get_project(
    project_id: uuid.UUID,
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    row = await session.execute(
        text("SELECT * FROM projects WHERE id = :id AND workspace_id = :ws"),
        {"id": str(project_id), "ws": str(ctx.workspace_id)},
    )
    r = row.fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Project 不存在")
    return ApiResponse(data=await _row_to_out(session, r))


# ── 更新 ────────────────────────────────────────────────────────────────────


@router.put("/{project_id}", response_model=ApiResponse[ProjectOut], summary="更新 Project")
async def update_project(
    project_id: uuid.UUID,
    body: ProjectUpdate,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    check = await session.execute(
        text("SELECT id FROM projects WHERE id = :id AND workspace_id = :ws"),
        {"id": str(project_id), "ws": str(ctx.workspace_id)},
    )
    if not check.fetchone():
        raise HTTPException(status_code=404, detail="Project 不存在")

    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=422, detail="未提供任何更新欄位")

    set_parts: list[str] = ["updated_at = :now", "updated_by = :by"]
    params: dict[str, Any] = {
        "id": str(project_id),
        "ws": str(ctx.workspace_id),
        "now": datetime.utcnow(),
        "by": str(ctx.user_id),
    }
    for k, v in updates.items():
        set_parts.append(f"{k} = :{k}")
        params[k] = v

    await session.execute(
        text(
            f"UPDATE projects SET {', '.join(set_parts)} "
            f"WHERE id = :id AND workspace_id = :ws"
        ),
        params,
    )
    row = await session.execute(
        text("SELECT * FROM projects WHERE id = :id"), {"id": str(project_id)},
    )
    return ApiResponse(data=await _row_to_out(session, row.fetchone()))


# ── 刪除 ────────────────────────────────────────────────────────────────────


@router.delete("/{project_id}", response_model=ApiResponse, summary="刪除 Project（admin）")
async def delete_project(
    project_id: uuid.UUID,
    ctx: TenantContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    check = await session.execute(
        text("SELECT id FROM projects WHERE id = :id AND workspace_id = :ws"),
        {"id": str(project_id), "ws": str(ctx.workspace_id)},
    )
    if not check.fetchone():
        raise HTTPException(status_code=404, detail="Project 不存在")
    await session.execute(
        text("DELETE FROM project_resources WHERE project_id = :id"),
        {"id": str(project_id)},
    )
    await session.execute(
        text("DELETE FROM projects WHERE id = :id AND workspace_id = :ws"),
        {"id": str(project_id), "ws": str(ctx.workspace_id)},
    )
    return ApiResponse(message="Project 已刪除")


# ── 資源連動：attach / detach ─────────────────────────────────────────────


async def _ensure_project_in_workspace(
    session: AsyncSession, project_id: uuid.UUID, workspace_id
) -> None:
    check = await session.execute(
        text("SELECT id FROM projects WHERE id = :id AND workspace_id = :ws"),
        {"id": str(project_id), "ws": str(workspace_id)},
    )
    if not check.fetchone():
        raise HTTPException(status_code=404, detail="Project 不存在")


@router.post(
    "/{project_id}/resources",
    response_model=ApiResponse[ProjectOut],
    summary="把 KB 或 Application 加入 Project",
)
async def attach_resource(
    project_id: uuid.UUID,
    body: AttachResource,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    await _ensure_project_in_workspace(session, project_id, ctx.workspace_id)
    # idempotent insert
    try:
        await session.execute(
            text(
                """
                INSERT INTO project_resources (project_id, kind, resource_id, attached_by)
                VALUES (:pid, :kind, :rid, :by)
                ON CONFLICT (project_id, kind, resource_id) DO NOTHING
                """
            ),
            {"pid": str(project_id), "kind": body.kind,
             "rid": body.resource_id, "by": str(ctx.user_id)},
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"加入資源失敗：{e}")

    row = await session.execute(
        text("SELECT * FROM projects WHERE id = :id"), {"id": str(project_id)},
    )
    return ApiResponse(data=await _row_to_out(session, row.fetchone()))


@router.delete(
    "/{project_id}/resources/{kind}/{resource_id}",
    response_model=ApiResponse[ProjectOut],
    summary="從 Project 移除指定 KB 或 Application",
)
async def detach_resource(
    project_id: uuid.UUID,
    kind: str,
    resource_id: str,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    if kind not in ("kb", "app"):
        raise HTTPException(status_code=400, detail="kind 必須是 'kb' 或 'app'")
    await _ensure_project_in_workspace(session, project_id, ctx.workspace_id)
    await session.execute(
        text(
            "DELETE FROM project_resources "
            "WHERE project_id = :pid AND kind = :kind AND resource_id = :rid"
        ),
        {"pid": str(project_id), "kind": kind, "rid": resource_id},
    )
    row = await session.execute(
        text("SELECT * FROM projects WHERE id = :id"), {"id": str(project_id)},
    )
    return ApiResponse(data=await _row_to_out(session, row.fetchone()))
