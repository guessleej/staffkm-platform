"""使用者管理 API（管理員用）"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext

from app.models.user import User, UserStatus
from staffkm_core.schemas.response import ApiResponse, PagedResponse, PageMeta
from staffkm_core.utils.database import get_session

router = APIRouter()
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


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
    model_config = {"from_attributes": True}


@router.get("", response_model=PagedResponse[UserOut])
async def list_users(page: int = 1, page_size: int = 20, session: AsyncSession = Depends(get_session)):
    offset = (page - 1) * page_size
    result = await session.execute(select(User).offset(offset).limit(page_size))
    users = result.scalars().all()
    total = await session.scalar(select(User).count()) or 0
    return PagedResponse(
        data=[UserOut.model_validate(u) for u in users],
        meta=PageMeta(page=page, page_size=page_size, total=total, total_pages=-(-total // page_size)),
    )


@router.post("", response_model=ApiResponse[UserOut])
async def create_user(body: UserCreate, session: AsyncSession = Depends(get_session)):
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
    return ApiResponse(data=UserOut.model_validate(user), message="使用者建立成功")


@router.patch("/{user_id}/status", response_model=ApiResponse)
async def update_user_status(
    user_id: uuid.UUID,
    status: UserStatus,
    session: AsyncSession = Depends(get_session),
):
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="使用者不存在")
    user.status = status
    return ApiResponse(message="使用者狀態已更新")
