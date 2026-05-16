"""API Key 管理 API — 讓外部系統可用 API Key 呼叫 Application（workspace-scoped）。

權限模型：
  list/create/delete/toggle  → require_admin  （僅 owner/admin 可管理）
  verify                     → 不需 workspace context（pre-auth），由
                                main.py 額外掛 `public_router` 暴露在
                                /api/v1/api-keys/verify
"""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session
from staffkm_tenant import TenantContext, require_admin

router = APIRouter()
public_router = APIRouter()  # 不掛 workspace 前綴；僅供 /verify


# ── Pydantic Schemas ────────────────────────────────────────────────────────


class ApiKeyCreate(BaseModel):
    name: str = Field(..., max_length=128)
    application_id: uuid.UUID
    expires_days: int | None = Field(default=None, ge=1)


class ApiKeyOut(BaseModel):
    id: uuid.UUID
    name: str
    application_id: uuid.UUID | None
    key_prefix: str
    is_active: bool
    created_at: datetime
    expires_at: datetime | None
    last_used_at: datetime | None
    created_by: str | None


class ApiKeyCreatedOut(ApiKeyOut):
    """建立時才有的回傳，包含完整 key（之後不再出現）"""
    full_key: str


class ApiKeyVerifyRequest(BaseModel):
    key: str = Field(..., description="完整 API Key，格式為 sk-{hex}")


def _row_to_out(row) -> ApiKeyOut:
    d = dict(row._mapping)
    d["is_active"] = d.get("status", "active") == "active"
    return ApiKeyOut(**{k: v for k, v in d.items() if k in ApiKeyOut.model_fields})


def _make_key() -> tuple[str, str, str]:
    """產生 (full_key, key_prefix, key_hash)"""
    full_key = f"sk-{secrets.token_hex(32)}"
    key_prefix = full_key[:8]
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    return full_key, key_prefix, key_hash


# ── 列表 ────────────────────────────────────────────────────────────────────


@router.get("", response_model=ApiResponse[list[ApiKeyOut]], summary="列出所有 API Keys")
async def list_api_keys(
    application_id: uuid.UUID | None = None,
    ctx: TenantContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    params: dict[str, Any] = {"workspace_id": str(ctx.workspace_id)}
    where = "WHERE workspace_id = :workspace_id"
    if application_id:
        where += " AND application_id = :application_id"
        params["application_id"] = str(application_id)

    rows = await session.execute(
        text(
            f"""
            SELECT id, name, application_id, key_prefix, status,
                   created_at, expires_at, last_used_at, created_by
            FROM api_keys
            {where}
            ORDER BY created_at DESC
            """
        ),
        params,
    )
    return ApiResponse(data=[_row_to_out(r) for r in rows.fetchall()])


# ── 建立 ────────────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=ApiResponse[ApiKeyCreatedOut],
    status_code=status.HTTP_201_CREATED,
    summary="建立 API Key（admin 以上）",
)
async def create_api_key(
    body: ApiKeyCreate,
    ctx: TenantContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    # 確認 application 存在且屬於同 workspace
    check = await session.execute(
        text(
            "SELECT id FROM applications "
            "WHERE id = :id AND workspace_id = :ws AND status != 'deleted'"
        ),
        {"id": str(body.application_id), "ws": str(ctx.workspace_id)},
    )
    if not check.fetchone():
        raise HTTPException(status_code=404, detail="應用程式不存在")

    full_key, key_prefix, key_hash = _make_key()
    new_id = uuid.uuid4()
    now = datetime.utcnow()
    expires_at = now + timedelta(days=body.expires_days) if body.expires_days else None
    created_by = str(ctx.user_id)

    await session.execute(
        text(
            """
            INSERT INTO api_keys (
                id, name, key_hash, key_prefix, application_id, workspace_id,
                expires_at, created_at, created_by, status
            ) VALUES (
                :id, :name, :key_hash, :key_prefix, :application_id, :workspace_id,
                :expires_at, :created_at, :created_by, 'active'
            )
            """
        ),
        {
            "id": str(new_id),
            "name": body.name,
            "key_hash": key_hash,
            "key_prefix": key_prefix,
            "application_id": str(body.application_id),
            "workspace_id": str(ctx.workspace_id),
            "expires_at": expires_at,
            "created_at": now,
            "created_by": created_by,
        },
    )

    row = await session.execute(
        text(
            """
            SELECT id, name, application_id, key_prefix, status,
                   created_at, expires_at, last_used_at, created_by
            FROM api_keys WHERE id = :id
            """
        ),
        {"id": str(new_id)},
    )
    key_row = row.fetchone()
    if not key_row:
        raise HTTPException(status_code=500, detail="API Key 建立失敗")

    out = _row_to_out(key_row)
    return ApiResponse(
        data=ApiKeyCreatedOut(**out.model_dump(), full_key=full_key),
        message="API Key 建立成功，請妥善保存，之後不再顯示完整金鑰",
    )


# ── 刪除 ────────────────────────────────────────────────────────────────────


@router.delete("/{key_id}", response_model=ApiResponse, summary="刪除 API Key")
async def delete_api_key(
    key_id: uuid.UUID,
    ctx: TenantContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    check = await session.execute(
        text("SELECT id FROM api_keys WHERE id = :id AND workspace_id = :ws"),
        {"id": str(key_id), "ws": str(ctx.workspace_id)},
    )
    if not check.fetchone():
        raise HTTPException(status_code=404, detail="API Key 不存在")

    await session.execute(
        text("DELETE FROM api_keys WHERE id = :id AND workspace_id = :ws"),
        {"id": str(key_id), "ws": str(ctx.workspace_id)},
    )
    return ApiResponse(message="API Key 已刪除")


# ── 切換啟用狀態 ─────────────────────────────────────────────────────────────


@router.patch("/{key_id}/toggle", response_model=ApiResponse[ApiKeyOut], summary="切換 API Key 啟用狀態")
async def toggle_api_key(
    key_id: uuid.UUID,
    ctx: TenantContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    row = await session.execute(
        text("SELECT id, status FROM api_keys WHERE id = :id AND workspace_id = :ws"),
        {"id": str(key_id), "ws": str(ctx.workspace_id)},
    )
    key_row = row.fetchone()
    if not key_row:
        raise HTTPException(status_code=404, detail="API Key 不存在")

    current_status = dict(key_row._mapping)["status"]
    new_status = "inactive" if current_status == "active" else "active"

    await session.execute(
        text("UPDATE api_keys SET status = :status WHERE id = :id AND workspace_id = :ws"),
        {"id": str(key_id), "ws": str(ctx.workspace_id), "status": new_status},
    )

    updated = await session.execute(
        text(
            """
            SELECT id, name, application_id, key_prefix, status,
                   created_at, expires_at, last_used_at, created_by
            FROM api_keys WHERE id = :id
            """
        ),
        {"id": str(key_id)},
    )
    return ApiResponse(
        data=_row_to_out(updated.fetchone()),
        message=f"API Key 已{'啟用' if new_status == 'active' else '停用'}",
    )


# ── 驗證（pre-auth，掛在 public_router → /api/v1/api-keys/verify）─────────


@public_router.post(
    "/verify",
    response_model=ApiResponse[dict],
    summary="驗證 API Key（不需 JWT、不需 workspace）",
)
async def verify_api_key(
    body: ApiKeyVerifyRequest,
    session: AsyncSession = Depends(get_session),
):
    key_hash = hashlib.sha256(body.key.encode()).hexdigest()

    row = await session.execute(
        text(
            """
            SELECT id, application_id, workspace_id, created_by, status, expires_at
            FROM api_keys
            WHERE key_hash = :key_hash
            """
        ),
        {"key_hash": key_hash},
    )
    key_row = row.fetchone()

    if not key_row:
        return ApiResponse(data={"valid": False})

    d = dict(key_row._mapping)

    if d["status"] != "active":
        return ApiResponse(data={"valid": False})

    if d["expires_at"] and d["expires_at"] < datetime.utcnow():
        return ApiResponse(data={"valid": False})

    await session.execute(
        text("UPDATE api_keys SET last_used_at = :now WHERE id = :id"),
        {"now": datetime.utcnow(), "id": str(d["id"])},
    )

    return ApiResponse(
        data={
            "valid": True,
            "application_id": str(d["application_id"]) if d["application_id"] else None,
            "workspace_id": str(d["workspace_id"]) if d["workspace_id"] else None,
            "created_by": d["created_by"],
        }
    )
