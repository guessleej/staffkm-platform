"""Workflow approvals API（v3.5 P2）。

workspace-scoped；member 可讀；admin 可 approve/reject。
"""
from __future__ import annotations
import uuid

from fastapi import APIRouter, Depends, Path, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session
from staffkm_tenant import TenantContext, require_admin, require_member

router = APIRouter()


class ResolveBody(BaseModel):
    note: str | None = None


def _serialize(row: dict) -> dict:
    """UUID / datetime / Decimal 安全化。"""
    out = dict(row)
    for k in ("id", "run_id", "approver_id"):
        if out.get(k) is not None:
            out[k] = str(out[k])
    return out


@router.get("", response_model=ApiResponse, summary="列出 approvals（含 pending）")
async def list_approvals(
    status: str | None = Query(default=None, description="filter: pending/approved/rejected"),
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    where = "workspace_id = :ws"
    params: dict = {"ws": str(ctx.workspace_id)}
    if status:
        where += " AND status = :status"
        params["status"] = status
    rows = await session.execute(text(f"""
        SELECT id, run_id, node_key, status, requester,
               approver_id, approver_note, payload,
               created_at, resolved_at
        FROM workflow_approvals
        WHERE {where}
        ORDER BY created_at DESC
        LIMIT 100
    """), params)
    items = [_serialize(dict(r._mapping)) for r in rows.fetchall()]
    return ApiResponse(data={"items": items})


async def _resolve(
    session: AsyncSession,
    ws_id,
    approval_id,
    new_status: str,
    note: str | None,
    approver_id: str | None,
):
    r = await session.execute(text("""
        UPDATE workflow_approvals
        SET status=:s, approver_id=:uid, approver_note=:note, resolved_at=now()
        WHERE id=:id AND workspace_id=:ws AND status='pending'
        RETURNING id
    """), {
        "s": new_status,
        "uid": approver_id,
        "note": note,
        "id": str(approval_id),
        "ws": str(ws_id),
    })
    if not r.fetchone():
        raise HTTPException(404, "approval not found or already resolved")
    await session.commit()


@router.post("/{approval_id}/approve", response_model=ApiResponse, summary="admin 同意")
async def approve(
    approval_id: uuid.UUID = Path(...),
    body: ResolveBody | None = None,
    ctx: TenantContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    await _resolve(
        session, ctx.workspace_id, approval_id, "approved",
        body.note if body else None,
        str(ctx.user_id) if ctx.user_id else None,
    )
    return ApiResponse(message="approved")


@router.post("/{approval_id}/reject", response_model=ApiResponse, summary="admin 拒絕")
async def reject(
    approval_id: uuid.UUID = Path(...),
    body: ResolveBody | None = None,
    ctx: TenantContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    await _resolve(
        session, ctx.workspace_id, approval_id, "rejected",
        body.note if body else None,
        str(ctx.user_id) if ctx.user_id else None,
    )
    return ApiResponse(message="rejected")
