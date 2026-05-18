"""Audit log writer — shared helper for all services.

v3.0 起把 _record() 從 services/agent/app/api/audit.py 搬到 shared package，
讓 knowledge / auth / agent 各 service 都能 import 同一份實作。

寫入 audit_logs 表（partitioned by created_at）。失敗應由 caller 用 try/except 包，
不要中斷原 endpoint 流程。
"""
from __future__ import annotations

import json as _json
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def record_audit(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID | None,
    actor_user_id: str | uuid.UUID | None,
    actor_username: str | None,
    action: str,
    entity_type: str,
    entity_id: str | uuid.UUID | None = None,
    entity_label: str | None = None,
    detail: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """寫一筆 audit log — 給各 service endpoint 內部呼叫。"""
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
