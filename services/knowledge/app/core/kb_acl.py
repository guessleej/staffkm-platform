"""KB 資源授權 enforce helper（v2.1 11-4）。

規則
- 無 kb_grants row → 沿用 workspace RBAC（任何 member 可讀，editor 以上可寫）
- 有任一 row → 白名單模式：
  - principal_type='workspace'（principal_id 視為通配）→ workspace 全體可以
  - principal_type='role'  且 principal_id 包含當前角色 → OK
  - principal_type='user'  且 principal_id == current user_id → OK
  - access='read' 至少要 read；access='edit' 必須 'edit' 或 'manage'

caller：在 read / write endpoints 前呼叫 enforce_kb_access(ctx, kb_id, session, need='read')
HTTP 403 詳細訊息：「您未獲授權存取此知識庫」
"""
from __future__ import annotations

import uuid
from typing import Literal

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from staffkm_tenant import TenantContext


_ACCESS_RANK = {"read": 0, "edit": 1, "manage": 2}


async def enforce_kb_access(
    ctx: TenantContext,
    kb_id: uuid.UUID,
    session: AsyncSession,
    *,
    need: Literal["read", "edit", "manage"] = "read",
) -> None:
    """符合 → return；不符合 → raise HTTPException(403)。"""
    # 先取所有 grant rows for this KB
    rows = await session.execute(
        text(
            "SELECT principal_type, principal_id, access "
            "FROM kb_grants WHERE kb_id = :kb AND workspace_id = :ws"
        ),
        {"kb": str(kb_id), "ws": str(ctx.workspace_id)},
    )
    grants = [dict(r._mapping) for r in rows.fetchall()]
    if not grants:
        # 預設模式：沿用 RBAC（caller 端的 require_member / require_writer 已驗證）
        return

    # 白名單模式
    user_id = str(ctx.user_id) if ctx.user_id else ""
    role    = ctx.role.value if hasattr(ctx, "role") and ctx.role else ""
    need_rank = _ACCESS_RANK[need]

    for g in grants:
        gt: str = g["principal_type"]
        gid: str = g["principal_id"]
        access: str = g.get("access") or "read"
        if _ACCESS_RANK.get(access, 0) < need_rank:
            continue
        if gt == "workspace":
            return  # workspace 全體授權
        if gt == "role" and gid == role:
            return
        if gt == "user" and gid == user_id:
            return

    raise HTTPException(status_code=403, detail="您未獲授權存取此知識庫")
