"""模型供應商與 AI 模型管理 API（管理員用）"""
import uuid
import base64
import httpx
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select, delete, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from staffkm_core.schemas.response import ApiResponse, PagedResponse, PageMeta
from staffkm_core.utils.database import get_session

router = APIRouter()

# ---------------------------------------------------------------------------
# 輔助函式 — API Key 混淆（base64）
# ---------------------------------------------------------------------------

def _encode_api_key(plain: str) -> str:
    """將明文 API Key 以 base64 編碼後儲存。"""
    return base64.b64encode(plain.encode()).decode()


def _decode_api_key(encoded: str) -> str:
    """將 base64 編碼的 API Key 還原為明文。"""
    return base64.b64decode(encoded.encode()).decode()


def _mask_api_key(encoded: str) -> str:
    """回傳 API Key 前綴（解碼後取前 8 字元）並遮罩其餘部分。"""
    try:
        plain = _decode_api_key(encoded)
        if len(plain) <= 8:
            return plain[:3] + "***"
        return plain[:8] + "***"
    except Exception:
        return "***"


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------

class ProviderCreate(BaseModel):
    name: str
    provider_type: str  # openai / ollama / azure / anthropic / custom
    base_url: str | None = None
    api_key: str | None = None
    config: dict[str, Any] | None = None


class ProviderUpdate(BaseModel):
    name: str | None = None
    provider_type: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    status: str | None = None
    config: dict[str, Any] | None = None


class ProviderOut(BaseModel):
    id: uuid.UUID
    name: str
    provider_type: str
    base_url: str | None
    api_key_prefix: str | None  # 遮罩後的前綴
    status: str
    config: dict[str, Any] | None
    tenant_id: str | None
    created_at: datetime
    updated_at: datetime
    created_by: str | None
    updated_by: str | None


class ModelCreate(BaseModel):
    model_name: str
    model_type: str  # llm / embedding / reranker / tts / stt
    display_name: str | None = None
    config: dict[str, Any] | None = None
    is_default: bool = False


class ModelUpdate(BaseModel):
    model_name: str | None = None
    model_type: str | None = None
    display_name: str | None = None
    config: dict[str, Any] | None = None
    is_default: bool | None = None
    status: str | None = None


class ModelOut(BaseModel):
    id: uuid.UUID
    provider_id: uuid.UUID
    model_name: str
    model_type: str
    display_name: str | None
    config: dict[str, Any] | None
    is_default: bool
    status: str
    price_per_1k_input_usd: float | None = None
    price_per_1k_output_usd: float | None = None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# 輔助 — 從原始 Row mapping 建立 ProviderOut
# ---------------------------------------------------------------------------

def _row_to_provider_out(row: Any) -> ProviderOut:
    api_key_prefix = _mask_api_key(row.api_key_enc) if row.api_key_enc else None
    return ProviderOut(
        id=row.id,
        name=row.name,
        provider_type=row.provider_type,
        base_url=row.base_url,
        api_key_prefix=api_key_prefix,
        status=row.status,
        config=row.config,
        tenant_id=row.tenant_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        created_by=row.created_by,
        updated_by=row.updated_by,
    )


def _row_to_model_out(row: Any) -> ModelOut:
    pin = getattr(row, "price_per_1k_input_usd", None)
    pout = getattr(row, "price_per_1k_output_usd", None)
    return ModelOut(
        id=row.id,
        provider_id=row.provider_id,
        model_name=row.model_name,
        model_type=row.model_type,
        display_name=row.display_name,
        config=row.config,
        is_default=row.is_default,
        status=row.status,
        price_per_1k_input_usd=float(pin) if pin is not None else None,
        price_per_1k_output_usd=float(pout) if pout is not None else None,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


# ---------------------------------------------------------------------------
# Provider 端點
# ---------------------------------------------------------------------------

@router.get("/providers", response_model=PagedResponse[ProviderOut], summary="列出所有模型供應商")
async def list_providers(
    page: int = 1,
    page_size: int = 20,
    request: Request = None,
    session: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    offset = (page - 1) * page_size

    from sqlalchemy import text
    count_result = await session.execute(text("SELECT COUNT(*) FROM model_providers"))
    total: int = count_result.scalar() or 0

    rows_result = await session.execute(
        text(
            "SELECT id, name, provider_type, base_url, api_key_enc, status, config, "
            "tenant_id, created_at, updated_at, created_by, updated_by "
            "FROM model_providers ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
        ),
        {"limit": page_size, "offset": offset},
    )
    rows = rows_result.fetchall()

    data = [_row_to_provider_out(r) for r in rows]
    return PagedResponse(
        data=data,
        meta=PageMeta(page=page, page_size=page_size, total=total, total_pages=-(-total // page_size)),
    )


@router.post("/providers", response_model=ApiResponse[ProviderOut], summary="建立模型供應商", status_code=201)
async def create_provider(
    body: ProviderCreate,
    request: Request = None,
    session: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    from sqlalchemy import text

    provider_id = uuid.uuid4()
    tenant_id = getattr(request.state, "tenant_id", None) if request else None
    created_by = getattr(request.state, "user_id", None) if request else None
    api_key_enc = _encode_api_key(body.api_key) if body.api_key else None

    import json
    config_json = json.dumps(body.config) if body.config else None

    await session.execute(
        text(
            "INSERT INTO model_providers (id, name, provider_type, base_url, api_key_enc, "
            "status, config, tenant_id, created_by, updated_by) "
            "VALUES (:id, :name, :provider_type, :base_url, :api_key_enc, "
            "'active', :config::jsonb, :tenant_id, :created_by, :updated_by)"
        ),
        {
            "id": str(provider_id),
            "name": body.name,
            "provider_type": body.provider_type,
            "base_url": body.base_url,
            "api_key_enc": api_key_enc,
            "config": config_json,
            "tenant_id": tenant_id,
            "created_by": created_by,
            "updated_by": created_by,
        },
    )

    row_result = await session.execute(
        text(
            "SELECT id, name, provider_type, base_url, api_key_enc, status, config, "
            "tenant_id, created_at, updated_at, created_by, updated_by "
            "FROM model_providers WHERE id = :id"
        ),
        {"id": str(provider_id)},
    )
    row = row_result.fetchone()
    return ApiResponse(data=_row_to_provider_out(row), message="模型供應商建立成功")


@router.get("/providers/{provider_id}", response_model=ApiResponse[ProviderOut], summary="取得供應商詳情")
async def get_provider(
    provider_id: uuid.UUID,
    request: Request = None,
    session: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    from sqlalchemy import text

    row_result = await session.execute(
        text(
            "SELECT id, name, provider_type, base_url, api_key_enc, status, config, "
            "tenant_id, created_at, updated_at, created_by, updated_by "
            "FROM model_providers WHERE id = :id"
        ),
        {"id": str(provider_id)},
    )
    row = row_result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="供應商不存在")
    return ApiResponse(data=_row_to_provider_out(row))


@router.put("/providers/{provider_id}", response_model=ApiResponse[ProviderOut], summary="更新供應商")
async def update_provider(
    provider_id: uuid.UUID,
    body: ProviderUpdate,
    request: Request = None,
    session: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    from sqlalchemy import text
    import json

    # 確認存在
    exist = await session.execute(
        text("SELECT id FROM model_providers WHERE id = :id"),
        {"id": str(provider_id)},
    )
    if not exist.fetchone():
        raise HTTPException(status_code=404, detail="供應商不存在")

    # 動態建立 SET 子句
    updates: list[str] = []
    params: dict[str, Any] = {"id": str(provider_id)}
    updated_by = getattr(request.state, "user_id", None) if request else None

    if body.name is not None:
        updates.append("name = :name")
        params["name"] = body.name
    if body.provider_type is not None:
        updates.append("provider_type = :provider_type")
        params["provider_type"] = body.provider_type
    if body.base_url is not None:
        updates.append("base_url = :base_url")
        params["base_url"] = body.base_url
    if body.api_key is not None:
        updates.append("api_key_enc = :api_key_enc")
        params["api_key_enc"] = _encode_api_key(body.api_key)
    if body.status is not None:
        updates.append("status = :status")
        params["status"] = body.status
    if body.config is not None:
        updates.append("config = :config::jsonb")
        params["config"] = json.dumps(body.config)

    updates.append("updated_at = NOW()")
    updates.append("updated_by = :updated_by")
    params["updated_by"] = updated_by

    await session.execute(
        text(f"UPDATE model_providers SET {', '.join(updates)} WHERE id = :id"),
        params,
    )

    row_result = await session.execute(
        text(
            "SELECT id, name, provider_type, base_url, api_key_enc, status, config, "
            "tenant_id, created_at, updated_at, created_by, updated_by "
            "FROM model_providers WHERE id = :id"
        ),
        {"id": str(provider_id)},
    )
    row = row_result.fetchone()
    return ApiResponse(data=_row_to_provider_out(row), message="供應商更新成功")


@router.delete("/providers/{provider_id}", response_model=ApiResponse, summary="刪除供應商")
async def delete_provider(
    provider_id: uuid.UUID,
    request: Request = None,
    session: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    from sqlalchemy import text

    result = await session.execute(
        text("DELETE FROM model_providers WHERE id = :id RETURNING id"),
        {"id": str(provider_id)},
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="供應商不存在")
    return ApiResponse(message="供應商已刪除")


@router.post("/providers/{provider_id}/verify", response_model=ApiResponse, summary="驗證供應商連線")
async def verify_provider(
    provider_id: uuid.UUID,
    request: Request = None,
    session: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    from sqlalchemy import text

    row_result = await session.execute(
        text(
            "SELECT provider_type, base_url, api_key_enc, config "
            "FROM model_providers WHERE id = :id"
        ),
        {"id": str(provider_id)},
    )
    row = row_result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="供應商不存在")

    provider_type = row.provider_type
    base_url = row.base_url
    api_key_enc = row.api_key_enc
    api_key = _decode_api_key(api_key_enc) if api_key_enc else None

    ok, detail = await _verify_connection(provider_type, base_url, api_key)
    if not ok:
        raise HTTPException(status_code=422, detail=f"連線驗證失敗：{detail}")
    return ApiResponse(message=f"連線驗證成功：{detail}")


# ---------------------------------------------------------------------------
# AI Model 端點
# ---------------------------------------------------------------------------

@router.get("/providers/{provider_id}/models", response_model=PagedResponse[ModelOut], summary="列出供應商的模型")
async def list_provider_models(
    provider_id: uuid.UUID,
    page: int = 1,
    page_size: int = 50,
    request: Request = None,
    session: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    from sqlalchemy import text

    # 確認供應商存在
    exist = await session.execute(
        text("SELECT id FROM model_providers WHERE id = :id"),
        {"id": str(provider_id)},
    )
    if not exist.fetchone():
        raise HTTPException(status_code=404, detail="供應商不存在")

    offset = (page - 1) * page_size
    count_result = await session.execute(
        text("SELECT COUNT(*) FROM ai_models WHERE provider_id = :provider_id"),
        {"provider_id": str(provider_id)},
    )
    total: int = count_result.scalar() or 0

    rows_result = await session.execute(
        text(
            "SELECT id, provider_id, model_name, model_type, display_name, config, "
            "is_default, status, price_per_1k_input_usd, price_per_1k_output_usd, "
            "created_at, updated_at "
            "FROM ai_models WHERE provider_id = :provider_id "
            "ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
        ),
        {"provider_id": str(provider_id), "limit": page_size, "offset": offset},
    )
    rows = rows_result.fetchall()
    data = [_row_to_model_out(r) for r in rows]
    return PagedResponse(
        data=data,
        meta=PageMeta(page=page, page_size=page_size, total=total, total_pages=-(-total // page_size)),
    )


@router.post("/providers/{provider_id}/models", response_model=ApiResponse[ModelOut], summary="新增模型定義", status_code=201)
async def create_model(
    provider_id: uuid.UUID,
    body: ModelCreate,
    request: Request = None,
    session: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    from sqlalchemy import text
    import json

    # 確認供應商存在
    exist = await session.execute(
        text("SELECT id FROM model_providers WHERE id = :id"),
        {"id": str(provider_id)},
    )
    if not exist.fetchone():
        raise HTTPException(status_code=404, detail="供應商不存在")

    model_id = uuid.uuid4()
    config_json = json.dumps(body.config) if body.config else None

    # 若設為預設，先取消同類型的其他預設
    if body.is_default:
        await session.execute(
            text(
                "UPDATE ai_models SET is_default = FALSE "
                "WHERE provider_id = :provider_id AND model_type = :model_type"
            ),
            {"provider_id": str(provider_id), "model_type": body.model_type},
        )

    await session.execute(
        text(
            "INSERT INTO ai_models (id, provider_id, model_name, model_type, display_name, "
            "config, is_default, status) "
            "VALUES (:id, :provider_id, :model_name, :model_type, :display_name, "
            ":config::jsonb, :is_default, 'active')"
        ),
        {
            "id": str(model_id),
            "provider_id": str(provider_id),
            "model_name": body.model_name,
            "model_type": body.model_type,
            "display_name": body.display_name or body.model_name,
            "config": config_json,
            "is_default": body.is_default,
        },
    )

    row_result = await session.execute(
        text(
            "SELECT id, provider_id, model_name, model_type, display_name, config, "
            "is_default, status, price_per_1k_input_usd, price_per_1k_output_usd, "
            "created_at, updated_at "
            "FROM ai_models WHERE id = :id"
        ),
        {"id": str(model_id)},
    )
    row = row_result.fetchone()
    return ApiResponse(data=_row_to_model_out(row), message="模型定義建立成功")


@router.put("/models/{model_id}", response_model=ApiResponse[ModelOut], summary="更新模型定義")
async def update_model(
    model_id: uuid.UUID,
    body: ModelUpdate,
    request: Request = None,
    session: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    from sqlalchemy import text
    import json

    exist_result = await session.execute(
        text("SELECT id, provider_id, model_type FROM ai_models WHERE id = :id"),
        {"id": str(model_id)},
    )
    existing = exist_result.fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="模型不存在")

    # 若設為預設，先取消同供應商同類型的其他預設
    target_type = body.model_type or existing.model_type
    if body.is_default:
        await session.execute(
            text(
                "UPDATE ai_models SET is_default = FALSE "
                "WHERE provider_id = :provider_id AND model_type = :model_type AND id != :id"
            ),
            {"provider_id": str(existing.provider_id), "model_type": target_type, "id": str(model_id)},
        )

    updates: list[str] = []
    params: dict[str, Any] = {"id": str(model_id)}

    if body.model_name is not None:
        updates.append("model_name = :model_name")
        params["model_name"] = body.model_name
    if body.model_type is not None:
        updates.append("model_type = :model_type")
        params["model_type"] = body.model_type
    if body.display_name is not None:
        updates.append("display_name = :display_name")
        params["display_name"] = body.display_name
    if body.config is not None:
        updates.append("config = :config::jsonb")
        params["config"] = json.dumps(body.config)
    if body.is_default is not None:
        updates.append("is_default = :is_default")
        params["is_default"] = body.is_default
    if body.status is not None:
        updates.append("status = :status")
        params["status"] = body.status

    updates.append("updated_at = NOW()")

    if updates:
        await session.execute(
            text(f"UPDATE ai_models SET {', '.join(updates)} WHERE id = :id"),
            params,
        )

    row_result = await session.execute(
        text(
            "SELECT id, provider_id, model_name, model_type, display_name, config, "
            "is_default, status, price_per_1k_input_usd, price_per_1k_output_usd, "
            "created_at, updated_at "
            "FROM ai_models WHERE id = :id"
        ),
        {"id": str(model_id)},
    )
    row = row_result.fetchone()
    return ApiResponse(data=_row_to_model_out(row), message="模型更新成功")


@router.delete("/models/{model_id}", response_model=ApiResponse, summary="刪除模型定義")
async def delete_model(
    model_id: uuid.UUID,
    request: Request = None,
    session: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    from sqlalchemy import text

    result = await session.execute(
        text("DELETE FROM ai_models WHERE id = :id RETURNING id"),
        {"id": str(model_id)},
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="模型不存在")
    return ApiResponse(message="模型已刪除")


@router.get("/models", response_model=PagedResponse[ModelOut], summary="列出所有模型（可依類型篩選）")
async def list_all_models(
    model_type: str | None = Query(None, description="llm / embedding / reranker / tts / stt"),
    page: int = 1,
    page_size: int = 50,
    request: Request = None,
    session: AsyncSession = Depends(get_session),
):
    _require_admin(request)
    from sqlalchemy import text

    offset = (page - 1) * page_size

    if model_type:
        count_result = await session.execute(
            text("SELECT COUNT(*) FROM ai_models WHERE model_type = :model_type"),
            {"model_type": model_type},
        )
        total: int = count_result.scalar() or 0
        rows_result = await session.execute(
            text(
                "SELECT id, provider_id, model_name, model_type, display_name, config, "
                "is_default, status, created_at, updated_at "
                "FROM ai_models WHERE model_type = :model_type "
                "ORDER BY is_default DESC, created_at DESC LIMIT :limit OFFSET :offset"
            ),
            {"model_type": model_type, "limit": page_size, "offset": offset},
        )
    else:
        count_result = await session.execute(text("SELECT COUNT(*) FROM ai_models"))
        total = count_result.scalar() or 0
        rows_result = await session.execute(
            text(
                "SELECT id, provider_id, model_name, model_type, display_name, config, "
                "is_default, status, created_at, updated_at "
                "FROM ai_models ORDER BY model_type, is_default DESC, created_at DESC "
                "LIMIT :limit OFFSET :offset"
            ),
            {"limit": page_size, "offset": offset},
        )

    rows = rows_result.fetchall()
    data = [_row_to_model_out(r) for r in rows]
    return PagedResponse(
        data=data,
        meta=PageMeta(page=page, page_size=page_size, total=total, total_pages=-(-total // page_size)),
    )


# ---------------------------------------------------------------------------
# 私有輔助函式
# ---------------------------------------------------------------------------

def _require_admin(request: Request | None) -> None:
    """檢查請求者是否擁有 admin 角色（從 Gateway 注入的標頭）。"""
    if request is None:
        return
    roles: list[str] = getattr(request.state, "roles", [])
    if "admin" not in roles and "superuser" not in roles:
        raise HTTPException(status_code=403, detail="需要管理員權限")


async def _verify_connection(
    provider_type: str,
    base_url: str | None,
    api_key: str | None,
) -> tuple[bool, str]:
    """向供應商發送測試請求，確認連線是否正常。"""
    timeout = httpx.Timeout(10.0)
    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        if provider_type == "ollama":
            url = (base_url or "http://localhost:11434").rstrip("/") + "/api/tags"
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url)
            if resp.status_code == 200:
                return True, f"Ollama 連線正常（{url}）"
            return False, f"HTTP {resp.status_code}"

        elif provider_type in ("openai", "custom"):
            url = (base_url or "https://api.openai.com/v1").rstrip("/") + "/models"
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                return True, "OpenAI 相容端點連線正常"
            return False, f"HTTP {resp.status_code}: {resp.text[:200]}"

        elif provider_type == "anthropic":
            url = (base_url or "https://api.anthropic.com").rstrip("/") + "/v1/models"
            anthropic_headers = {
                "x-api-key": api_key or "",
                "anthropic-version": "2023-06-01",
            }
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url, headers=anthropic_headers)
            if resp.status_code == 200:
                return True, "Anthropic 連線正常"
            return False, f"HTTP {resp.status_code}: {resp.text[:200]}"

        elif provider_type == "azure":
            # Azure OpenAI: base_url 應為 https://<resource>.openai.azure.com/
            if not base_url:
                return False, "Azure 供應商需提供 base_url"
            url = base_url.rstrip("/") + "/openai/models?api-version=2024-02-01"
            azure_headers = {"api-key": api_key or ""}
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url, headers=azure_headers)
            if resp.status_code == 200:
                return True, "Azure OpenAI 連線正常"
            return False, f"HTTP {resp.status_code}: {resp.text[:200]}"

        else:
            return False, f"不支援的供應商類型：{provider_type}"

    except httpx.ConnectError as exc:
        return False, f"無法連線：{exc}"
    except httpx.TimeoutException:
        return False, "連線逾時"
    except Exception as exc:
        return False, str(exc)
