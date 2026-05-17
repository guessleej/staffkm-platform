"""OIDC SSO endpoints (v2.4-B).

最小可用版本：
- GET /auth/oidc/info     — 前端問「SSO 是否啟用」+ 顯示名
- GET /auth/oidc/login    — redirect 到 IdP authorize endpoint
- GET /auth/oidc/callback — IdP 回 code → 換 token → fetch userinfo → upsert User → 簽 JWT

用 secrets.token_urlsafe 產 state（CSRF 防護）放 cookie；callback 比對。
無需 redis；state cookie 5 分鐘 TTL。
"""
from __future__ import annotations

import secrets
import time
import uuid
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt as _jwt
import structlog
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth_service import AuthService
from app.models.user import User
from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session

log = structlog.get_logger()
router = APIRouter()

_STATE_COOKIE = "staffkm_oidc_state"
_STATE_TTL_SEC = 300


def _enabled() -> None:
    if not settings.OIDC_ENABLED:
        raise HTTPException(status_code=404, detail="OIDC not enabled")
    for k in ('OIDC_ISSUER', 'OIDC_CLIENT_ID', 'OIDC_CLIENT_SECRET', 'OIDC_REDIRECT_URI'):
        if not getattr(settings, k):
            raise HTTPException(status_code=500, detail=f"missing {k}")


async def _discover() -> dict[str, Any]:
    """OIDC discovery — issuer 的 /.well-known/openid-configuration。"""
    url = settings.OIDC_ISSUER.rstrip('/') + '/.well-known/openid-configuration'
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(url)
        r.raise_for_status()
        return r.json()


def _sign_state(extra: dict | None = None) -> str:
    payload = {
        'nonce': secrets.token_urlsafe(16),
        'exp':   int(time.time()) + _STATE_TTL_SEC,
        **(extra or {}),
    }
    return _jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')


def _verify_state(token: str) -> dict | None:
    try:
        return _jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
    except Exception:
        return None


@router.get("/info", response_model=ApiResponse)
async def info():
    return ApiResponse(data={
        'enabled':       settings.OIDC_ENABLED,
        'display_name':  settings.OIDC_DISPLAY_NAME,
    })


@router.get("/login")
async def oidc_login(request: Request, next: str = '/'):
    _enabled()
    discovery = await _discover()
    state = _sign_state({'next': next if next.startswith('/') else '/'})
    auth_url = discovery['authorization_endpoint'] + '?' + urlencode({
        'response_type': 'code',
        'client_id':     settings.OIDC_CLIENT_ID,
        'redirect_uri':  settings.OIDC_REDIRECT_URI,
        'scope':         settings.OIDC_SCOPES,
        'state':         state,
    })
    resp = RedirectResponse(auth_url, status_code=302)
    resp.set_cookie(
        _STATE_COOKIE, state,
        max_age=_STATE_TTL_SEC, httponly=True, samesite='lax',
        secure=request.url.scheme == 'https',
    )
    return resp


@router.get("/callback")
async def oidc_callback(
    code: str,
    state: str,
    state_cookie: str | None = Cookie(default=None, alias=_STATE_COOKIE),
    session: AsyncSession = Depends(get_session),
):
    _enabled()
    # CSRF：state 必須跟 cookie 內的一致
    if not state_cookie or state_cookie != state:
        raise HTTPException(status_code=400, detail="state mismatch")
    payload = _verify_state(state)
    if not payload:
        raise HTTPException(status_code=400, detail="state invalid or expired")
    next_path = payload.get('next', '/')

    discovery = await _discover()

    # 1. 換 token
    async with httpx.AsyncClient(timeout=10) as c:
        token_resp = await c.post(discovery['token_endpoint'], data={
            'grant_type':    'authorization_code',
            'code':          code,
            'redirect_uri':  settings.OIDC_REDIRECT_URI,
            'client_id':     settings.OIDC_CLIENT_ID,
            'client_secret': settings.OIDC_CLIENT_SECRET,
        })
        token_resp.raise_for_status()
        tok = token_resp.json()

        # 2. fetch userinfo
        userinfo_resp = await c.get(
            discovery['userinfo_endpoint'],
            headers={'Authorization': f"Bearer {tok['access_token']}"},
        )
        userinfo_resp.raise_for_status()
        userinfo = userinfo_resp.json()

    email = userinfo.get('email')
    if not email:
        raise HTTPException(status_code=400, detail="OIDC userinfo missing email")

    sub = userinfo.get('sub') or email
    name = userinfo.get('name') or userinfo.get('preferred_username') or email.split('@')[0]

    # 3. upsert user — v3.0：優先用 oidc_sub 比對，再 fallback email
    res = await session.execute(select(User).where(User.oidc_sub == sub))
    user = res.scalar_one_or_none()
    if not user:
        # 用 email 再找一次（既有 user 第一次 SSO 自動連結）
        res = await session.execute(select(User).where(User.email == email))
        user = res.scalar_one_or_none()
    if not user:
        user = User(
            id=uuid.uuid4(),
            username=email.split('@')[0][:60],
            email=email,
            display_name=name,
            roles=[settings.OIDC_DEFAULT_ROLE],
            oidc_sub=sub,                            # v3.0 正規欄
            oidc_issuer=settings.OIDC_ISSUER,
            password_hash=None,
            status='active',
        )
        session.add(user)
        await session.commit()
        log.info("oidc_user_created", email=email, sub=sub)
    else:
        # 既有 user 第一次 SSO → 補 oidc_sub / 更新 display_name
        changed = False
        if name and user.display_name != name:
            user.display_name = name; changed = True
        if user.oidc_sub != sub:
            user.oidc_sub = sub; changed = True
        if user.oidc_issuer != settings.OIDC_ISSUER:
            user.oidc_issuer = settings.OIDC_ISSUER; changed = True
        if changed:
            await session.commit()

    # 4. 簽 staffKM JWT
    svc = AuthService(session)
    tokens = svc.generate_tokens(user)

    # 5. redirect 回前端，帶 access_token 在 hash 片段（不會送上 server log）
    target = f"{next_path}#access_token={tokens['access_token']}&refresh_token={tokens['refresh_token']}"
    resp = RedirectResponse(target, status_code=302)
    resp.delete_cookie(_STATE_COOKIE)
    return resp
