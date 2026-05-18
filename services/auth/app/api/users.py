"""使用者管理 API（管理員用）"""
import logging
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext

from app.models.user import User, UserStatus
from staffkm_core.audit import record_audit
from staffkm_core.schemas.response import ApiResponse, PagedResponse, PageMeta
from staffkm_core.utils.database import get_session

logger = logging.getLogger(__name__)
router = APIRouter()
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def _safe_audit(session: AsyncSession, **kwargs) -> None:
    try:
        await record_audit(session, **kwargs)
    except Exception as exc:  # noqa: BLE001
        logger.warning("audit record failed: %s", exc)


class UserCreate(BaseModel):
    username: str
    email: str | None = None
    display_name: str | None = None
    password: str
    roles: list[str] = ["user"]
    department: str | None = None


class UserOut(BaseModel):
    id: uuid.UUID
    username: str
    email: str | None
    display_name: str | None
    status: str
    roles: list[str]
    department: str | None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = {"from_attributes": True}


@router.get("", response_model=PagedResponse[UserOut])
async def list_users(
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(User)
    count_stmt = select(func.count()).select_from(User)
    if search:
        like = f"%{search}%"
        cond = or_(User.username.ilike(like), User.email.ilike(like), User.display_name.ilike(like))
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)
    offset = (page - 1) * page_size
    result = await session.execute(stmt.order_by(User.username).offset(offset).limit(page_size))
    users = result.scalars().all()
    total = await session.scalar(count_stmt) or 0
    return PagedResponse(
        data=[UserOut.model_validate(u) for u in users],
        meta=PageMeta(page=page, page_size=page_size, total=total, total_pages=-(-total // page_size)),
    )


@router.post("", response_model=ApiResponse[UserOut])
async def create_user(
    body: UserCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    user = User(
        username=body.username,
        email=body.email,
        display_name=body.display_name,
        password_hash=pwd_ctx.hash(body.password),
        roles=body.roles,
        department=body.department,
        status=UserStatus.ACTIVE,
    )
    session.add(user)
    await session.flush()
    actor_user_id = getattr(request.state, "user_id", None)
    await _safe_audit(
        session,
        workspace_id=None,
        actor_user_id=actor_user_id,
        actor_username=None,
        action="create",
        entity_type="user",
        entity_id=str(user.id),
        entity_label=user.username,
        detail={"roles": body.roles, "department": body.department},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()
    return ApiResponse(data=UserOut.model_validate(user), message="使用者建立成功")


@router.patch("/{user_id}/status", response_model=ApiResponse)
async def update_user_status(
    user_id: uuid.UUID,
    status: UserStatus,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="使用者不存在")
    old_status = user.status.value if hasattr(user.status, "value") else str(user.status)
    user.status = status
    actor_user_id = getattr(request.state, "user_id", None)
    new_status = status.value if hasattr(status, "value") else str(status)
    await _safe_audit(
        session,
        workspace_id=None,
        actor_user_id=actor_user_id,
        actor_username=None,
        action="update",
        entity_type="user",
        entity_id=str(user_id),
        entity_label=user.username,
        detail={"status": {"old": old_status, "new": new_status}},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()
    return ApiResponse(message="使用者狀態已更新")


# ── v5.0.1：admin 補完 users API ──────────────────────────────────────────
class RoleUpdate(BaseModel):
    roles: list[str] = Field(..., min_length=1)


class PasswordReset(BaseModel):
    new_password: str = Field(..., min_length=8)


@router.put("/{user_id}/role", response_model=ApiResponse)
async def update_user_role(
    user_id: uuid.UUID,
    body: RoleUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="使用者不存在")
    old_roles = list(user.roles or [])
    user.roles = body.roles
    actor_user_id = getattr(request.state, "user_id", None)
    await _safe_audit(
        session,
        workspace_id=None,
        actor_user_id=actor_user_id,
        actor_username=None,
        action="update",
        entity_type="user",
        entity_id=str(user_id),
        entity_label=user.username,
        detail={"roles": {"old": old_roles, "new": body.roles}},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()
    return ApiResponse(message="角色已更新")


@router.post("/{user_id}/reset-password", response_model=ApiResponse)
async def reset_user_password(
    user_id: uuid.UUID,
    body: PasswordReset,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="使用者不存在")
    user.password_hash = pwd_ctx.hash(body.new_password)
    actor_user_id = getattr(request.state, "user_id", None)
    await _safe_audit(
        session,
        workspace_id=None,
        actor_user_id=actor_user_id,
        actor_username=None,
        action="reset_password",
        entity_type="user",
        entity_id=str(user_id),
        entity_label=user.username,
        detail={},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()
    return ApiResponse(message="密碼已重設")


@router.delete("/{user_id}", response_model=ApiResponse)
async def delete_user(
    user_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """軟刪除：將 status 設為 inactive 並改 username（避免 unique 衝突）。"""
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="使用者不存在")
    actor_user_id = getattr(request.state, "user_id", None)
    if actor_user_id and str(actor_user_id) == str(user_id):
        raise HTTPException(status_code=400, detail="不可刪除自己")
    original_username = user.username
    user.status = UserStatus.INACTIVE
    # 釋放 username / email unique 鎖，方便未來 re-invite
    user.username = f"{original_username}__deleted_{uuid.uuid4().hex[:8]}"
    if user.email:
        user.email = f"deleted_{uuid.uuid4().hex[:8]}__{user.email}"
    await _safe_audit(
        session,
        workspace_id=None,
        actor_user_id=actor_user_id,
        actor_username=None,
        action="delete",
        entity_type="user",
        entity_id=str(user_id),
        entity_label=original_username,
        detail={"soft_delete": True},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()
    return ApiResponse(message="使用者已刪除")
