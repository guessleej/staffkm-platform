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


def _require_admin(request: Request) -> None:
    """🔒 安全（critical）：使用者管理 API（增/刪/改角色/重設密碼/列表）一律限 admin。
    角色來自 Gateway 從「驗證過的 JWT」注入的 request.state.roles（X-User-Roles，
    gateway 已剝除 client 偽造值）。缺此守衛 → 任何登入者可 PUT 自己的 role=admin 提權、
    或重設他人密碼接管帳號。以 router 層級 dependency 套用，涵蓋本檔所有（含未來）端點。"""
    roles = getattr(request.state, "roles", []) or []
    if "admin" not in roles and "superuser" not in roles:
        raise HTTPException(status_code=403, detail="需要管理員權限")


# router 層級依賴 → 本檔每個端點進來前都先過 admin 檢查
router = APIRouter(dependencies=[Depends(_require_admin)])
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
    # v2.7 X-Pack：per-user 登入方式白名單（NULL = 全部允許）
    allowed_login_methods: list[str] | None = None
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


# ── v2.7 X-Pack：per-user 登入方式白名單 ─────────────────────────────
_ALLOWED_METHODS = {"password", "ldap", "oidc", "google", "github", "local"}


class LoginMethodsUpdate(BaseModel):
    # None / 不傳 = 不限制（清空白名單）；空 list 視為不限制
    allowed_login_methods: list[str] | None = None


@router.put("/{user_id}/login-methods", response_model=ApiResponse)
async def update_user_login_methods(
    user_id: uuid.UUID,
    body: LoginMethodsUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """設定使用者允許的登入方式。None / 空 list = 不限制（全部允許）。"""
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="使用者不存在")
    methods = body.allowed_login_methods
    if methods is not None:
        invalid = [m for m in methods if m not in _ALLOWED_METHODS]
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=f"不支援的登入方式：{invalid}（可用：{sorted(_ALLOWED_METHODS)}）",
            )
        # 空 list 視為 NULL，避免使用者完全鎖死
        if not methods:
            methods = None
    old = list(user.allowed_login_methods) if user.allowed_login_methods else None
    user.allowed_login_methods = methods
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
        detail={"allowed_login_methods": {"old": old, "new": methods}},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()
    return ApiResponse(message="登入方式白名單已更新", data={"allowed_login_methods": methods})


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
