"""Email verify / password reset — v4.6 F.

Public endpoints（gateway PUBLIC_PATHS / PUBLIC_PREFIXES 已加 prefix）。

- verify-email/send    : 給未驗證 user resend；不洩漏 email 是否存在
- verify-email/confirm : token 24h 內有效
- forgot-password      : 不洩漏 email 是否存在；token 1h 有效
- reset-password       : 換 bcrypt hash

注意：users 表用 `status='active'`（不是 is_active boolean），對齊 User model。
"""
from __future__ import annotations
import datetime as dt
import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session
from app.core.email import send_email
from app.config import settings

router = APIRouter()


def _gen_token() -> str:
    return secrets.token_urlsafe(32)


def _web_base() -> str:
    return (settings.PUBLIC_WEB_BASE_URL or "http://localhost").rstrip("/")


# ── Email verification ──────────────────────────────────────────────

class VerifyEmailSendRequest(BaseModel):
    email: EmailStr


class VerifyEmailConfirmRequest(BaseModel):
    token: str = Field(..., min_length=10, max_length=128)


@router.post("/verify-email/send", response_model=ApiResponse,
             summary="Resend verification email")
async def send_verify(
    body: VerifyEmailSendRequest,
    session: AsyncSession = Depends(get_session),
):
    """給未驗證的 user resend verify email。不洩漏 email 是否存在。"""
    token = _gen_token()
    exp = dt.datetime.utcnow() + dt.timedelta(hours=24)
    r = await session.execute(text("""
        UPDATE users SET verify_token = :t, verify_token_exp = :e
        WHERE email = :em AND email_verified_at IS NULL
        RETURNING id
    """), {"t": token, "e": exp, "em": body.email})
    row = r.fetchone()
    if not row:
        # 不洩漏；一律回 200
        return ApiResponse(message="if email exists, verification link sent")
    await session.commit()

    link = f"{_web_base()}/verify-email?token={token}"
    await send_email(
        to=body.email,
        subject="[staffKM] Verify your email",
        body=f"Click to verify your email:\n\n{link}\n\nLink valid for 24 hours.",
    )
    return ApiResponse(message="verification email sent")


@router.post("/verify-email/confirm", response_model=ApiResponse,
             summary="Confirm email with token")
async def confirm_verify(
    body: VerifyEmailConfirmRequest,
    session: AsyncSession = Depends(get_session),
):
    r = await session.execute(text("""
        UPDATE users
           SET email_verified_at = now(),
               verify_token      = NULL,
               verify_token_exp  = NULL
         WHERE verify_token = :t AND verify_token_exp > now()
         RETURNING id, email
    """), {"t": body.token})
    row = r.fetchone()
    if not row:
        raise HTTPException(400, "invalid or expired token")
    await session.commit()
    return ApiResponse(data={"email": row.email}, message="email verified")


# ── Password reset ──────────────────────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=10, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


@router.post("/forgot-password", response_model=ApiResponse,
             summary="Request password reset link")
async def forgot_password(
    body: ForgotPasswordRequest,
    session: AsyncSession = Depends(get_session),
):
    token = _gen_token()
    exp = dt.datetime.utcnow() + dt.timedelta(hours=1)
    r = await session.execute(text("""
        UPDATE users SET reset_token = :t, reset_token_exp = :e
        WHERE email = :em AND status = 'active'
        RETURNING id
    """), {"t": token, "e": exp, "em": body.email})
    if r.fetchone():
        await session.commit()
        link = f"{_web_base()}/reset-password?token={token}"
        await send_email(
            to=body.email,
            subject="[staffKM] Password reset",
            body=(
                f"Click to reset your password:\n\n{link}\n\n"
                "Valid for 1 hour. Ignore this email if you did not request a reset."
            ),
        )
    # 一律 200，不洩漏 email 是否存在
    return ApiResponse(message="if email exists, reset link sent")


@router.post("/reset-password", response_model=ApiResponse,
             summary="Confirm password reset")
async def reset_password(
    body: ResetPasswordRequest,
    session: AsyncSession = Depends(get_session),
):
    r = await session.execute(text("""
        SELECT id FROM users
         WHERE reset_token = :t AND reset_token_exp > now()
    """), {"t": body.token})
    row = r.fetchone()
    if not row:
        raise HTTPException(400, "invalid or expired token")

    from passlib.hash import bcrypt
    pwd_hash = bcrypt.hash(body.new_password)

    await session.execute(text("""
        UPDATE users
           SET password_hash         = :p,
               must_change_password  = false,
               reset_token           = NULL,
               reset_token_exp       = NULL
         WHERE id = :id
    """), {"p": pwd_hash, "id": str(row.id)})
    await session.commit()
    return ApiResponse(message="password reset successful")
