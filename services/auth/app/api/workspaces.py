"""Workspace CRUD + Member 管理 API（RFC-001 Stage 2）。"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.workspace import (
    MemberInvite, MemberOut, MemberRoleUpdate,
    WorkspaceCreate, WorkspaceOut, WorkspaceUpdate,
)
from app.services.workspace_service import WorkspaceService
from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session

router = APIRouter()


def _current_user_id(request: Request) -> uuid.UUID:
    raw = getattr(request.state, "user_id", None)
    if not raw:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="尚未登入")
    try:
        return uuid.UUID(raw)
    except (TypeError, ValueError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="X-User-ID 格式錯誤")


# ─── Workspace ────────────────────────────────────────────────────────

@router.get("", response_model=ApiResponse[list[WorkspaceOut]], summary="列出我的所有工作區")
async def list_workspaces(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    user_id = _current_user_id(request)
    svc = WorkspaceService(session)
    items = await svc.list_for_user(user_id)
    return ApiResponse(data=[WorkspaceOut.model_validate(x) for x in items])


@router.post("", response_model=ApiResponse[WorkspaceOut], status_code=status.HTTP_201_CREATED,
             summary="建立新工作區（呼叫者自動成為 owner）")
async def create_workspace(
    body:    WorkspaceCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    user_id = _current_user_id(request)
    svc = WorkspaceService(session)
    ws = await svc.create(body.name, body.slug, body.description, user_id)
    out = WorkspaceOut.model_validate({**ws.__dict__, "role": "owner", "member_count": 1})
    return ApiResponse(data=out, message="工作區已建立")


@router.get("/{ws_id}", response_model=ApiResponse[WorkspaceOut], summary="工作區詳細")
async def get_workspace(
    ws_id:   uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    user_id = _current_user_id(request)
    svc = WorkspaceService(session)
    data = await svc.get(ws_id, user_id)
    return ApiResponse(data=WorkspaceOut.model_validate(data))


@router.patch("/{ws_id}", response_model=ApiResponse[WorkspaceOut], summary="編輯工作區（admin+）")
async def update_workspace(
    ws_id:   uuid.UUID,
    body:    WorkspaceUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    user_id = _current_user_id(request)
    svc = WorkspaceService(session)
    ws = await svc.update(ws_id, user_id, body.name, body.description)
    data = await svc.get(ws_id, user_id)
    return ApiResponse(data=WorkspaceOut.model_validate(data), message="工作區已更新")


@router.delete("/{ws_id}", response_model=ApiResponse, summary="軟刪除工作區（owner 限定）")
async def delete_workspace(
    ws_id:   uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    user_id = _current_user_id(request)
    svc = WorkspaceService(session)
    await svc.soft_delete(ws_id, user_id)
    return ApiResponse(message="工作區已刪除")


# ─── Members ──────────────────────────────────────────────────────────

@router.get("/{ws_id}/members", response_model=ApiResponse[list[MemberOut]], summary="列成員")
async def list_members(
    ws_id:   uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    user_id = _current_user_id(request)
    svc = WorkspaceService(session)
    items = await svc.list_members(ws_id, user_id)
    return ApiResponse(data=[MemberOut.model_validate(x) for x in items])


@router.post("/{ws_id}/members", response_model=ApiResponse[MemberOut],
             status_code=status.HTTP_201_CREATED, summary="加成員（admin+）")
async def invite_member(
    ws_id:   uuid.UUID,
    body:    MemberInvite,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    user_id = _current_user_id(request)
    svc = WorkspaceService(session)
    member = await svc.invite(ws_id, user_id, body.user_id, body.role)
    items = await svc.list_members(ws_id, user_id)
    new = next(x for x in items if x["user_id"] == member.user_id)
    return ApiResponse(data=MemberOut.model_validate(new), message="已加入成員")


@router.patch("/{ws_id}/members/{user_id}", response_model=ApiResponse[MemberOut],
              summary="改成員角色（admin+）")
async def update_member_role(
    ws_id:    uuid.UUID,
    user_id:  uuid.UUID,
    body:     MemberRoleUpdate,
    request:  Request,
    session:  AsyncSession = Depends(get_session),
):
    actor_id = _current_user_id(request)
    svc = WorkspaceService(session)
    await svc.update_role(ws_id, actor_id, user_id, body.role)
    items = await svc.list_members(ws_id, actor_id)
    updated = next(x for x in items if x["user_id"] == user_id)
    return ApiResponse(data=MemberOut.model_validate(updated), message="角色已更新")


@router.delete("/{ws_id}/members/{user_id}", response_model=ApiResponse, summary="移除成員（admin+）")
async def remove_member(
    ws_id:    uuid.UUID,
    user_id:  uuid.UUID,
    request:  Request,
    session:  AsyncSession = Depends(get_session),
):
    actor_id = _current_user_id(request)
    svc = WorkspaceService(session)
    await svc.remove(ws_id, actor_id, user_id)
    return ApiResponse(message="成員已移除")
