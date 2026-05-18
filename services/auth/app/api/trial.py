"""Trial signup — v4.1 A。

Public endpoint，不需 auth。建 trial workspace + admin user + workspace_member。
14 天試用期；agent service 的 trial_expiry_worker 過期後會把 workspace
標記 is_frozen=TRUE。

注意：
- workspace 是 singular table name（對齊 0001_workspace.sql + tenant 套件 ORM）
- 不沿用 v3.4 SMTP（在 agent service）— welcome email 留 TODO，best-effort 不阻擋。
"""
from __future__ import annotations
import datetime as dt
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext

from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session

router = APIRouter()
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TrialSignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    workspace_name: str = Field(..., min_length=2, max_length=64)


@router.post("/trial", response_model=ApiResponse, summary="Public 14-day trial signup")
async def trial_signup(
    body: TrialSignupRequest,
    session: AsyncSession = Depends(get_session),
):
    """建 trial workspace + admin user。14 天試用期。"""
    # 0. email 唯一檢查
    r = await session.execute(
        text("SELECT 1 FROM users WHERE email = :e LIMIT 1"),
        {"e": body.email},
    )
    if r.scalar_one_or_none():
        raise HTTPException(409, "email already registered")

    # 1. 建 workspace（trial）— 用 singular table name
    expires_at = dt.datetime.utcnow() + dt.timedelta(days=14)
    ws_id = str(uuid.uuid4())
    # slug 從 workspace_name 衍生 + 短 uuid 後綴避免衝突
    slug_base = "".join(c.lower() if c.isalnum() else "-" for c in body.workspace_name).strip("-") or "ws"
    ws_slug = f"{slug_base[:40]}-{ws_id[:6]}"

    await session.execute(text("""
        INSERT INTO workspace (
            id, name, slug, plan, quota_meta,
            trial_expires_at, trial_plan, signup_email, signup_source,
            created_at, updated_at
        ) VALUES (
            :id, :name, :slug, 'free', '{}'::jsonb,
            :exp, 'free-trial', :email, 'self-service',
            now(), now()
        )
    """), {
        "id": ws_id, "name": body.workspace_name, "slug": ws_slug,
        "exp": expires_at, "email": body.email,
    })

    # 2. 建 user（hashed password via passlib bcrypt — 跟 users.py 一致）
    pwd_hash = pwd_ctx.hash(body.password)
    user_id = str(uuid.uuid4())
    username = body.email.split("@")[0] + "_" + ws_id[:4]
    await session.execute(text("""
        INSERT INTO users (id, username, email, password_hash, status, roles)
        VALUES (:id, :u, :e, :p, 'active', ARRAY['user']::varchar[])
    """), {"id": user_id, "u": username, "e": body.email, "p": pwd_hash})

    # 3. 建 workspace_member（admin role）— PK 為 id (uuid)，uniq(workspace_id,user_id)
    await session.execute(text("""
        INSERT INTO workspace_member (id, workspace_id, user_id, role, is_active, invited_at, joined_at)
        VALUES (:mid, :ws, :uid, 'admin', TRUE, now(), now())
    """), {"mid": str(uuid.uuid4()), "ws": ws_id, "uid": user_id})

    await session.commit()

    # 4. send welcome email (best-effort — auth service 暫無 SMTP wrapper，留 TODO)
    # v4.1 後續：複製 agent service 的 app/core/email.py 進 auth service
    # 或抽到 staffkm_core/utils/email.py 共用。
    try:
        from app.core.email import send_email  # noqa: F401  (placeholder)
    except Exception:
        pass

    return ApiResponse(
        data={
            "workspace_id": ws_id,
            "user_id": user_id,
            "trial_expires_at": expires_at.isoformat(),
            "next_step": "login with your email and password",
        },
        message="trial signup successful (14-day free trial)",
    )
