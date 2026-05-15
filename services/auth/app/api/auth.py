"""身分驗證 API — 登入、登出、Token 刷新"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_service import AuthService
from core.schemas.response import ApiResponse
from core.utils.database import get_session

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: dict


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/login", response_model=ApiResponse[TokenResponse], summary="帳號密碼登入")
async def login(body: LoginRequest, session: AsyncSession = Depends(get_session)):
    svc = AuthService(session)
    user = await svc.authenticate(body.username, body.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="帳號或密碼錯誤",
        )

    tokens = svc.generate_tokens(user)
    return ApiResponse(
        data=TokenResponse(
            **tokens,
            user={
                "id": str(user.id),
                "username": user.username,
                "display_name": user.display_name,
                "email": user.email,
                "roles": user.roles,
                "department": user.department,
            },
        ),
        message="登入成功",
    )


@router.post("/refresh", response_model=ApiResponse, summary="刷新 Access Token")
async def refresh_token(body: RefreshRequest, session: AsyncSession = Depends(get_session)):
    import jwt
    from app.config import settings
    try:
        payload = jwt.decode(body.refresh_token, settings.SECRET_KEY, algorithms=["HS256"])
        if payload.get("type") != "refresh":
            raise ValueError("非 refresh token")
    except Exception:
        raise HTTPException(status_code=401, detail="無效的 Refresh Token")

    from sqlalchemy import select
    from app.models.user import User
    user = await session.get(User, payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="使用者不存在")

    svc = AuthService(session)
    tokens = svc.generate_tokens(user)
    return ApiResponse(data=tokens, message="Token 刷新成功")


@router.post("/logout", response_model=ApiResponse, summary="登出")
async def logout(request: Request):
    # Token 黑名單可由 Redis 實作，此處為基礎版本
    return ApiResponse(message="登出成功")


@router.get("/me", response_model=ApiResponse, summary="取得目前使用者資訊")
async def me(request: Request, session: AsyncSession = Depends(get_session)):
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="未驗證")
    from app.models.user import User
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="使用者不存在")
    return ApiResponse(data={
        "id": str(user.id),
        "username": user.username,
        "display_name": user.display_name,
        "email": user.email,
        "roles": user.roles,
        "department": user.department,
    })
