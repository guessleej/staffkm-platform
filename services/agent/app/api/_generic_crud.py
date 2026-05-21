"""通用 workspace-scoped CRUD router 工廠（RFC-006 新 backlog）。

讓 tools / skills / data_sources 三個新模組共用同一段 CRUD 邏輯，
只需傳入 table_name + pydantic schema 即可生成完整 router。

注意：複雜的執行 / 同步 / 預覽 邏輯由各模組另開 endpoint 補上。
本工廠只負責「列表 / 取得 / 建立 / 更新 / 刪除」基本面。
"""
import json
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session
from staffkm_tenant import TenantContext, require_admin, require_member, require_writer


def make_crud_router(
    *,
    table:       str,
    out_model:   type[BaseModel],
    create_model: type[BaseModel],
    update_model: type[BaseModel],
    jsonb_fields: tuple[str, ...] = (),
) -> APIRouter:
    """產生一份完整的 workspace-scoped CRUD router。

    Args:
        table:        資料表名稱（必須有 id, workspace_id, created_at/by, updated_at/by 欄位）
        out_model:    輸出 schema（傳給前端的 row shape）
        create_model: POST body schema
        update_model: PUT body schema
        jsonb_fields: 哪些欄位是 JSONB（INSERT/UPDATE 時要 ::jsonb cast、輸出時要解析）
    """
    router = APIRouter()

    def _normalize(d: dict[str, Any]) -> dict[str, Any]:
        for f in jsonb_fields:
            if isinstance(d.get(f), str):
                try: d[f] = json.loads(d[f])
                except Exception: pass
        return d

    @router.get("", response_model=ApiResponse[list[out_model]], summary=f"列出 {table}")
    async def list_items(
        ctx: TenantContext = Depends(require_member),
        session: AsyncSession = Depends(get_session),
    ):
        rows = await session.execute(
            text(f"SELECT * FROM {table} WHERE workspace_id = :ws ORDER BY created_at DESC"),
            {"ws": str(ctx.workspace_id)},
        )
        items = [_normalize(dict(r._mapping)) for r in rows.fetchall()]
        return ApiResponse(data=[out_model(**x) for x in items])

    @router.get("/{item_id}", response_model=ApiResponse[out_model], summary=f"取得 {table} 詳情")
    async def get_item(
        item_id: uuid.UUID,
        ctx: TenantContext = Depends(require_member),
        session: AsyncSession = Depends(get_session),
    ):
        row = await session.execute(
            text(f"SELECT * FROM {table} WHERE id = :id AND workspace_id = :ws"),
            {"id": str(item_id), "ws": str(ctx.workspace_id)},
        )
        r = row.fetchone()
        if not r:
            raise HTTPException(status_code=404, detail="資源不存在")
        return ApiResponse(data=out_model(**_normalize(dict(r._mapping))))

    @router.post(
        "",
        response_model=ApiResponse[out_model],
        status_code=status.HTTP_201_CREATED,
        summary=f"建立 {table}",
    )
    async def create_item(
        body: create_model,
        ctx: TenantContext = Depends(require_writer),
        session: AsyncSession = Depends(get_session),
    ):
        d = body.model_dump()
        new_id = uuid.uuid4()
        now = datetime.utcnow()
        cols = ["id", "workspace_id", *d.keys(), "created_at", "updated_at", "created_by"]
        placeholders = []
        params: dict[str, Any] = {
            "id": str(new_id),
            "workspace_id": str(ctx.workspace_id),
            "now": now,
            "created_by": str(ctx.user_id),
        }
        for k, v in d.items():
            if k in jsonb_fields:
                # CLAUDE.md §8：用 CAST(:p AS jsonb)，不可 :p::jsonb（asyncpg dialect 雷）
                placeholders.append(f"CAST(:{k} AS jsonb)")
                params[k] = json.dumps(v, ensure_ascii=False)
            else:
                placeholders.append(f":{k}")
                params[k] = v
        cols_sql = ", ".join(cols)
        ph_sql = ", ".join([":id", ":workspace_id", *placeholders, ":now", ":now", ":created_by"])
        await session.execute(
            text(f"INSERT INTO {table} ({cols_sql}) VALUES ({ph_sql})"),
            params,
        )
        row = await session.execute(
            text(f"SELECT * FROM {table} WHERE id = :id"), {"id": str(new_id)},
        )
        return ApiResponse(data=out_model(**_normalize(dict(row.fetchone()._mapping))))

    @router.put("/{item_id}", response_model=ApiResponse[out_model], summary=f"更新 {table}")
    async def update_item(
        item_id: uuid.UUID,
        body: update_model,
        ctx: TenantContext = Depends(require_writer),
        session: AsyncSession = Depends(get_session),
    ):
        chk = await session.execute(
            text(f"SELECT id FROM {table} WHERE id = :id AND workspace_id = :ws"),
            {"id": str(item_id), "ws": str(ctx.workspace_id)},
        )
        if not chk.fetchone():
            raise HTTPException(status_code=404, detail="資源不存在")
        updates = body.model_dump(exclude_unset=True)
        if not updates:
            raise HTTPException(status_code=422, detail="未提供任何更新欄位")
        set_parts = ["updated_at = :now", "updated_by = :by"]
        params: dict[str, Any] = {
            "id": str(item_id), "ws": str(ctx.workspace_id),
            "now": datetime.utcnow(), "by": str(ctx.user_id),
        }
        for k, v in updates.items():
            if k in jsonb_fields:
                # CLAUDE.md §8：用 CAST(:p AS jsonb)，不可 :p::jsonb（asyncpg dialect 雷）
                set_parts.append(f"{k} = CAST(:{k} AS jsonb)")
                params[k] = json.dumps(v, ensure_ascii=False)
            else:
                set_parts.append(f"{k} = :{k}")
                params[k] = v
        await session.execute(
            text(f"UPDATE {table} SET {', '.join(set_parts)} WHERE id = :id AND workspace_id = :ws"),
            params,
        )
        row = await session.execute(
            text(f"SELECT * FROM {table} WHERE id = :id"), {"id": str(item_id)},
        )
        return ApiResponse(data=out_model(**_normalize(dict(row.fetchone()._mapping))))

    @router.delete("/{item_id}", response_model=ApiResponse, summary=f"刪除 {table}（admin）")
    async def delete_item(
        item_id: uuid.UUID,
        ctx: TenantContext = Depends(require_admin),
        session: AsyncSession = Depends(get_session),
    ):
        chk = await session.execute(
            text(f"SELECT id FROM {table} WHERE id = :id AND workspace_id = :ws"),
            {"id": str(item_id), "ws": str(ctx.workspace_id)},
        )
        if not chk.fetchone():
            raise HTTPException(status_code=404, detail="資源不存在")
        await session.execute(
            text(f"DELETE FROM {table} WHERE id = :id AND workspace_id = :ws"),
            {"id": str(item_id), "ws": str(ctx.workspace_id)},
        )
        return ApiResponse(message="已刪除")

    return router
