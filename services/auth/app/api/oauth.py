"""Self-service OAuth (Google / GitHub) — v4.6 F.

與 v2.4 OIDC SSO（企業 admin manual config，services/auth/app/api/oidc.py）
並行不衝突：這條是 end-user 自助走 Google / GitHub 登入，自動 create user。

env：
- GOOGLE_OAUTH_CLIENT_ID / _SECRET
- GITHUB_OAUTH_CLIENT_ID / _SECRET

state 簡化策略（v4.6）：endpoint 回 `state` 給前端 cookie/localStorage 自存，
callback 不強制驗 state（OAuth provider 仍會 echo state 回來，但前端負責比對）。
v4.x 後續可改 server-side redis cookie。
"""
from __future__ import annotations
import secrets
from typing import Literal
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session

from app.config import settings
from app.core.auth_service import AuthService
from app.models.user import User, UserStatus

router = APIRouter()


def _providers() -> dict[str, dict[str, str]]:
    """Lazy 讀 settings — 測試時可改 env reload。"""
    return {
        "google": {
            "client_id":     settings.GOOGLE_OAUTH_CLIENT_ID,
            "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
            "auth_url":      "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url":     "https://oauth2.googleapis.com/token",
            "userinfo_url":  "https://openidconnect.googleapis.com/v1/userinfo",
            "scope":         "openid email profile",
        },
        "github": {
            "client_id":     settings.GITHUB_OAUTH_CLIENT_ID,
            "client_secret": settings.GITHUB_OAUTH_CLIENT_SECRET,
            "auth_url":      "https://github.com/login/oauth/authorize",
            "token_url":     "https://github.com/login/oauth/access_token",
            "userinfo_url":  "https://api.github.com/user",
            "scope":         "read:user user:email",
        },
    }


@router.get("/{provider}/authorize", response_model=ApiResponse,
            summary="Start OAuth flow (returns authorize_url)")
async def authorize(
    provider: Literal["google", "github"],
    request_url: str = Query(..., description="前端 base URL，用來組 redirect_uri"),
):
    cfg = _providers()[provider]
    if not cfg["client_id"]:
        raise HTTPException(503, f"{provider} OAuth not configured")
    state = secrets.token_urlsafe(16)
    # redirect_uri 指向「前端」route，由前端再呼叫 /callback API 拿 token。
    # 這樣 OAuth provider 跳回後 user 看到的是 SPA 頁面而非裸 JSON。
    redirect_uri = f"{request_url.rstrip('/')}/oauth/callback/{provider}"
    params = {
        "client_id":     cfg["client_id"],
        "redirect_uri":  redirect_uri,
        "response_type": "code",
        "scope":         cfg["scope"],
        "state":         state,
    }
    return ApiResponse(data={
        "authorize_url": f"{cfg['auth_url']}?{urlencode(params)}",
        "state":         state,
        "redirect_uri":  redirect_uri,
    })


@router.get("/{provider}/callback", response_model=ApiResponse, summary="OAuth callback")
async def callback(
    provider: Literal["google", "github"],
    code: str = Query(...),
    state: str = Query(...),  # noqa: ARG001  前端負責比對
    session: AsyncSession = Depends(get_session),
):
    """Exchange code → access_token → userinfo → find-or-create user → JWT。"""
    import httpx
    cfg = _providers()[provider]
    if not cfg["client_id"]:
        raise HTTPException(503, f"{provider} OAuth not configured")

    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post(
                cfg["token_url"],
                data={
                    "client_id":     cfg["client_id"],
                    "client_secret": cfg["client_secret"],
                    "code":          code,
                    "grant_type":    "authorization_code",
                },
                headers={"Accept": "application/json"},
            )
            r.raise_for_status()
            access_token = r.json().get("access_token")
            if not access_token:
                raise HTTPException(400, "no access_token from provider")

            r2 = await c.get(
                cfg["userinfo_url"],
                headers={"Authorization": f"Bearer {access_token}"},
            )
            r2.raise_for_status()
            info = r2.json()
    except httpx.HTTPError as e:
        raise HTTPException(502, f"oauth provider error: {e}")

    email = info.get("email")
    if not email:
        # GitHub 可能 hide primary email → 補打 /user/emails
        if provider == "github":
            try:
                async with httpx.AsyncClient(timeout=10) as c:
                    r3 = await c.get(
                        "https://api.github.com/user/emails",
                        headers={"Authorization": f"Bearer {access_token}"},
                    )
                    r3.raise_for_status()
                    for e_row in r3.json():
                        if e_row.get("primary") and e_row.get("verified"):
                            email = e_row.get("email")
                            break
            except httpx.HTTPError:
                pass
    if not email:
        raise HTTPException(400, "email not available from oauth provider")

    sub = str(info.get("id") or info.get("sub") or "")

    # Find or create user
    r4 = await session.execute(
        text("SELECT id FROM users WHERE email = :e"), {"e": email}
    )
    row = r4.fetchone()
    is_new_user = False
    if row:
        user_id = str(row.id)
    else:
        import uuid
        user_id = str(uuid.uuid4())
        username = (email.split("@")[0] + "_" + user_id[:4])[:64]
        display_name = info.get("name") or info.get("login") or email.split("@")[0]
        await session.execute(text("""
            INSERT INTO users (
                id, username, email, display_name,
                password_hash, status, roles,
                email_verified_at, oidc_sub, oidc_issuer
            ) VALUES (
                :id, :u, :e, :dn,
                '', 'active', ARRAY['user']::varchar[],
                now(), :sub, :iss
            )
        """), {
            "id": user_id, "u": username, "e": email, "dn": display_name,
            "sub": sub, "iss": provider,
        })
        await session.commit()
        is_new_user = True

    # Issue JWT — 用 AuthService.generate_tokens（與 /login 一致）
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(500, "user lookup failed after create")
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(403, "account disabled")

    # v2.7 X-Pack：per-user 登入方式白名單（google / github）
    from app.api.auth import _check_method_allowed
    _check_method_allowed(user, provider)

    tokens = AuthService(session).generate_tokens(user)

    return ApiResponse(data={
        **tokens,
        "user": {
            "id":           str(user.id),
            "username":     user.username,
            "display_name": user.display_name,
            "email":        user.email,
            "roles":        user.roles,
        },
        "is_new_user": is_new_user,
        "provider":    provider,
    })
