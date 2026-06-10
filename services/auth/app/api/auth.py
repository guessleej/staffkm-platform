"""身分驗證 API — 登入、登出、Token 刷新"""
import jwt as _jwt
import random
import time
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_service import AuthService
from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session

router = APIRouter()


# ── Sprint 20-B / v3.0：失敗次數追蹤（Redis-backed，多 instance ready）─
# 升級自 v2.x 的 in-process counter；多 gateway / auth replica 部署正確
import redis.asyncio as _aioredis
from app.config import settings as _settings

_FAIL_THRESHOLD = 3       # 連續失敗達此數即要求 CAPTCHA
_FAIL_TTL_SEC   = 600     # 10 分鐘窗口
_redis_client: _aioredis.Redis | None = None
_REDIS_PREFIX = "staffkm:auth:fail:"
# fallback：Redis 連不到時退回 in-process
_failed_attempts: dict[str, list[float]] = defaultdict(list)

def _get_redis() -> _aioredis.Redis | None:
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = _aioredis.from_url(_settings.REDIS_URL, decode_responses=True)
        except Exception as e:
            log_msg = f"redis init failed, fallback to in-process: {e}"
            import structlog; structlog.get_logger().warning(log_msg)
            _redis_client = None
    return _redis_client


def _fail_key(req: Request, username: str) -> str:
    ip = (req.headers.get('x-forwarded-for') or req.client.host or 'unknown').split(',')[0].strip()
    return f"{ip}:{username.lower()}"


async def _fail_count(key: str) -> int:
    """Redis: INCR 後讀目前值；連不上 → fallback in-process。"""
    r = _get_redis()
    if r:
        try:
            v = await r.get(_REDIS_PREFIX + key)
            return int(v) if v else 0
        except Exception:
            pass
    # fallback
    now = time.time()
    arr = _failed_attempts[key]
    arr[:] = [t for t in arr if now - t < _FAIL_TTL_SEC]
    return len(arr)


async def _fail_record(key: str) -> None:
    r = _get_redis()
    if r:
        try:
            full = _REDIS_PREFIX + key
            # INCR + EXPIRE 一個 pipeline（也可用 NX 但保持簡單）
            async with r.pipeline(transaction=False) as pipe:
                await pipe.incr(full).expire(full, _FAIL_TTL_SEC).execute()
            return
        except Exception:
            pass
    _failed_attempts[key].append(time.time())


async def _fail_clear(key: str) -> None:
    r = _get_redis()
    if r:
        try:
            await r.delete(_REDIS_PREFIX + key); return
        except Exception:
            pass
    _failed_attempts.pop(key, None)


def _check_method_allowed(user, method: str) -> None:
    """v2.7 X-Pack：若 user.allowed_login_methods 不為 NULL 且不含 method → 401。"""
    allowed = getattr(user, "allowed_login_methods", None)
    if allowed is None:
        return
    # 防呆：空 list 視為「全部不允許」，比 NULL 更嚴
    if method not in (allowed or []):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"login_method_not_allowed:{method}",
        )


class LoginRequest(BaseModel):
    username: str
    password: str
    captcha_token: str | None = None
    captcha_answer: str | None = None


class CaptchaOut(BaseModel):
    token:    str   # signed JWT，含 answer + exp
    question: str   # 顯示給人看的算式


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: dict


class RefreshRequest(BaseModel):
    refresh_token: str


@router.get("/captcha", response_model=ApiResponse[CaptchaOut], summary="取得數學 CAPTCHA")
async def get_captcha():
    """產生 a + b = ? 或 a - b = ? 簡單算式。token 為簽過的 JWT，5 分鐘內有效。"""
    from app.config import settings
    op = random.choice(['+', '-'])
    a = random.randint(2, 9)
    b = random.randint(2, 9)
    if op == '-' and b > a: a, b = b, a
    answer = a + b if op == '+' else a - b
    token = _jwt.encode(
        {"a": answer, "exp": int(time.time()) + 300},
        settings.SECRET_KEY, algorithm="HS256",
    )
    return ApiResponse(data=CaptchaOut(token=token, question=f"{a} {op} {b} = ?"))


def _verify_captcha(token: str, answer: str) -> bool:
    from app.config import settings
    try:
        payload = _jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return str(payload.get("a")) == answer.strip()
    except Exception:
        return False


@router.post("/login", response_model=ApiResponse[TokenResponse], summary="帳號密碼登入")
async def login(body: LoginRequest, request: Request, session: AsyncSession = Depends(get_session)):
    fkey = _fail_key(request, body.username)
    fails = await _fail_count(fkey)

    # 連續 N 次失敗後強制要求 CAPTCHA
    if fails >= _FAIL_THRESHOLD:
        if not body.captcha_token or not body.captcha_answer:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="captcha_required",
            )
        if not _verify_captcha(body.captcha_token, body.captcha_answer):
            await _fail_record(fkey)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="captcha_invalid",
            )

    svc = AuthService(session)
    user = await svc.authenticate(body.username, body.password)

    if not user:
        await _fail_record(fkey)
        new_fails = await _fail_count(fkey)
        # 達到門檻時告訴前端需要 CAPTCHA
        detail = "captcha_required" if new_fails >= _FAIL_THRESHOLD else "帳號或密碼錯誤"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        )

    # v2.7 X-Pack：驗證 per-user 登入方式白名單（password 走本地、ldap_dn 表示 LDAP）
    method = "ldap" if getattr(user, "ldap_dn", None) else "password"
    _check_method_allowed(user, method)

    # 成功 → 清零失敗計數
    await _fail_clear(fkey)

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
                # v5.12：首登強制改密旗標，前端據此攔截導向改密
                "must_change_password": bool(getattr(user, "must_change_password", False)),
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
        # v2.7 X-Pack
        "allowed_login_methods": user.allowed_login_methods,
        # v5.12：首登強制改密 — 前端登入後若 true 強制導向改密
        "must_change_password": bool(getattr(user, "must_change_password", False)),
        # v5.13 #2：上次使用的 workspace（前端 load() 無 localStorage 時用它當預設）
        "last_workspace_id": str(user.last_workspace_id) if getattr(user, "last_workspace_id", None) else None,
    })


class LastWorkspaceRequest(BaseModel):
    workspace_id: str


@router.put("/me/last-workspace", response_model=ApiResponse, summary="記住上次使用的 workspace")
async def set_last_workspace(
    body: LastWorkspaceRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    # v5.13 #2：前端切 workspace 時寫回，跨裝置/來源記住偏好。
    # 不嚴格驗證 workspace_id 歸屬（純使用者偏好；前端 load() 會對照清單，無效就退預設）。
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="未驗證")
    import uuid as _uuid
    try:
        ws_uuid = _uuid.UUID(body.workspace_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=422, detail="workspace_id 格式錯誤")
    from app.models.user import User
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="使用者不存在")
    user.last_workspace_id = ws_uuid
    await session.commit()
    return ApiResponse(message="已記住")


class ChangeMyPasswordRequest(BaseModel):
    current_password: str | None = None       # 已有密碼者必填；純 SSO 帳號可省
    new_password: str = Field(..., min_length=8, max_length=128)


@router.post("/change-password", response_model=ApiResponse, summary="變更自己的密碼（已登入）")
async def change_my_password(
    body: ChangeMyPasswordRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """v5.12：已登入使用者改自己密碼，並清除 must_change_password（首登強制改密用）。"""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="未驗證")
    from app.models.user import User
    from passlib.hash import bcrypt
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="使用者不存在")
    # 已有密碼者必須驗證目前密碼（防 session 被盜後直接改密）；純 SSO（password_hash 空）可豁免
    if user.password_hash:
        if not body.current_password or not bcrypt.verify(body.current_password, user.password_hash):
            raise HTTPException(status_code=400, detail="目前密碼不正確")
        if body.current_password == body.new_password:
            raise HTTPException(status_code=400, detail="新密碼不可與目前密碼相同")
    user.password_hash = bcrypt.hash(body.new_password)
    user.must_change_password = False
    await session.commit()
    return ApiResponse(message="密碼已更新")
