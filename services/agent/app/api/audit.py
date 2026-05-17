"""Audit log API (v3.0 — Production Hardening)。

利用既有 audit_logs 表（partitioned by created_at）。v3 起補上：
  - workspace_id   — 多租戶 filter
  - actor_username — 顯示用，不必每次 JOIN users
  - entity_label   — 操作標的人可讀名稱

API：
  GET /admin/audit-logs?actor=&action=&resource=&since=&page=&page_size=

寫入呼叫 _record() helper（其他 endpoint 內部用）。
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from staffkm_core.schemas.response import PagedResponse, PageMeta
from staffkm_core.utils.database import get_session
from staffkm_tenant import TenantContext, require_admin

router = APIRouter()


@router.get("", response_model=PagedResponse, summary="列出 audit logs (admin only)")
async def list_audit_logs(
    actor: str | None = Query(default=None, description="filter user_id"),
    action: str | None = Query(default=None),
    resource: str | None = Query(default=None, description="entity type — application/kb/project/api_key/template/user"),
    since: str | None = Query(default=None, description="ISO timestamp"),
    page: int = 1,
    page_size: int = 50,
    ctx: TenantContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    where = ["(workspace_id = :ws OR workspace_id IS NULL)"]
    params: dict[str, Any] = {"ws": str(ctx.workspace_id)}
    if actor:
        where.append("user_id = :actor"); params["actor"] = actor
    if action:
        where.append("action = :action"); params["action"] = action
    if resource:
        where.append("resource = :resource"); params["resource"] = resource
    if since:
        where.append("created_at >= :since"); params["since"] = since

    where_clause = " AND ".join(where)
    params["limit"] = page_size
    params["offset"] = (page - 1) * page_size

    rows = await session.execute(
        text(f"""
            SELECT id, user_id AS actor_user_id, actor_username,
                   action, resource AS entity_type, resource_id AS entity_id,
                   entity_label, payload AS detail,
                   ip_address::text AS ip_address, user_agent, created_at
            FROM audit_logs
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """),
        params,
    )
    items = [dict(r._mapping) for r in rows.fetchall()]

    count_row = await session.execute(
        text(f"SELECT count(*) AS c FROM audit_logs WHERE {where_clause}"),
        {k: v for k, v in params.items() if k not in ('limit', 'offset')},
    )
    total = count_row.scalar_one()

    return PagedResponse(
        data=items,
        meta=PageMeta(
            page=page, page_size=page_size, total=total,
            total_pages=-(-total // page_size),
        ),
    )


async def _record(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID | None,
    actor_user_id: str | None,
    actor_username: str | None,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    entity_label: str | None = None,
    detail: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """寫一筆 audit log — 給其他 endpoint 內部呼叫。"""
    import json as _json
    await session.execute(
        text("""
            INSERT INTO audit_logs (
                id, workspace_id, user_id, actor_username,
                action, resource, resource_id, entity_label,
                payload, ip_address, user_agent, created_at
            ) VALUES (
                gen_random_uuid(), :ws, :actor, :uname,
                :action, :etype, :eid, :elabel,
                CAST(:detail AS jsonb),
                CAST(NULLIF(:ip, '') AS inet), :ua, now()
            )
        """),
        {
            "ws": str(workspace_id) if workspace_id else None,
            "actor": str(actor_user_id) if actor_user_id else None,
            "uname": actor_username,
            "action": action,
            "etype": entity_type,
            "eid": str(entity_id) if entity_id else None,
            "elabel": entity_label,
            "detail": _json.dumps(detail or {}, ensure_ascii=False),
            "ip": ip_address or "",
            "ua": user_agent,
        },
    )
