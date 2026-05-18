"""Event Trigger API（M4 啟動）。

- GET    /triggers                     列出 workspace 內的 triggers
- POST   /triggers                     新建（require_writer）
- PUT    /triggers/{id}                更新（require_writer）
- DELETE /triggers/{id}                刪除（require_writer）
- GET    /triggers/{id}/runs           列出 run 歷史
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session
from staffkm_tenant import TenantContext, require_member, require_writer

router = APIRouter()


_VALID_KINDS = ("interval", "cron", "webhook")


class TriggerCreate(BaseModel):
    application_id: str
    name:           str = Field(..., min_length=1, max_length=128)
    kind:           str = Field(default="interval")
    cron_expr:      str | None = None
    interval_sec:   int | None = None
    input_template: str = ""
    enabled:        bool = True


class TriggerUpdate(BaseModel):
    name:           str | None = None
    cron_expr:      str | None = None
    interval_sec:   int | None = None
    input_template: str | None = None
    enabled:        bool | None = None


def _check_kind_payload(body: TriggerCreate | TriggerUpdate, kind: str) -> None:
    if kind not in _VALID_KINDS:
        raise HTTPException(status_code=400, detail=f"kind 必須為 {_VALID_KINDS} 之一")
    if kind == "interval" and (not getattr(body, "interval_sec", None) or body.interval_sec <= 0):
        raise HTTPException(status_code=400, detail="kind=interval 必須提供正整數 interval_sec")
    if kind == "cron" and not getattr(body, "cron_expr", None):
        raise HTTPException(status_code=400, detail="kind=cron 必須提供 cron_expr")


def _compute_next_fire(kind: str, interval_sec: int | None) -> datetime | None:
    if kind == "interval" and interval_sec and interval_sec > 0:
        return datetime.utcnow() + timedelta(seconds=interval_sec)
    if kind == "cron":
        try:
            from croniter import croniter  # type: ignore
        except ImportError:
            return None
        # 沒有 cron_expr 在 caller 處檢；此處假設 caller 已驗證
        return None  # 真正計算交給 trigger_worker._next_fire（avoid duplication）
    return None


@router.get("", response_model=ApiResponse, summary="列出 triggers")
async def list_triggers(
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    rows = await session.execute(
        text(
            """
            SELECT id, application_id, name, kind, cron_expr, interval_sec,
                   enabled, next_fire_at, last_fired_at, last_status, last_error,
                   created_at, updated_at
            FROM event_triggers
            WHERE workspace_id = :ws
            ORDER BY created_at DESC
            """
        ),
        {"ws": str(ctx.workspace_id)},
    )
    return ApiResponse(data=[dict(r._mapping) for r in rows.fetchall()])


@router.post("", response_model=ApiResponse, summary="建立 trigger")
async def create_trigger(
    body: TriggerCreate,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    _check_kind_payload(body, body.kind)
    # 檢查 application 屬於同 workspace
    chk = await session.execute(
        text("SELECT id FROM applications WHERE id = :id AND workspace_id = :ws AND status != 'deleted'"),
        {"id": body.application_id, "ws": str(ctx.workspace_id)},
    )
    if not chk.fetchone():
        raise HTTPException(status_code=404, detail="application 不存在")

    nfa = _compute_next_fire(body.kind, body.interval_sec)
    if body.kind == "cron":
        # 由 worker 在第一次 tick 時計算
        nfa = datetime.utcnow()  # 立刻評估
    tid = str(uuid.uuid4())
    await session.execute(
        text(
            """
            INSERT INTO event_triggers (
                id, workspace_id, application_id, name, kind, cron_expr, interval_sec,
                input_template, enabled, next_fire_at, created_by
            ) VALUES (
                :id, :ws, :app, :name, :kind, :cron, :ivl,
                :tpl, :en, :nfa, :by
            )
            """
        ),
        {
            "id":   tid,
            "ws":   str(ctx.workspace_id),
            "app":  body.application_id,
            "name": body.name,
            "kind": body.kind,
            "cron": body.cron_expr,
            "ivl":  body.interval_sec,
            "tpl":  body.input_template,
            "en":   body.enabled,
            "nfa":  nfa,
            "by":   str(ctx.user_id) if ctx.user_id else None,
        },
    )
    return ApiResponse(data={"id": tid}, message="trigger 已建立")


@router.put("/{trigger_id}", response_model=ApiResponse, summary="更新 trigger")
async def update_trigger(
    trigger_id: uuid.UUID,
    body: TriggerUpdate,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    sets: list[str] = ["updated_at = now()"]
    params: dict[str, Any] = {"id": str(trigger_id), "ws": str(ctx.workspace_id)}
    for col, val in body.dict(exclude_unset=True).items():
        sets.append(f"{col} = :{col}")
        params[col] = val
    if len(sets) == 1:
        return ApiResponse(message="no-op")
    sql = f"UPDATE event_triggers SET {', '.join(sets)} WHERE id = :id AND workspace_id = :ws"
    res = await session.execute(text(sql), params)
    if res.rowcount == 0:
        raise HTTPException(status_code=404, detail="trigger 不存在")
    return ApiResponse(message="trigger 已更新")


@router.delete("/{trigger_id}", response_model=ApiResponse, summary="刪除 trigger")
async def delete_trigger(
    trigger_id: uuid.UUID,
    ctx: TenantContext = Depends(require_writer),
    session: AsyncSession = Depends(get_session),
):
    res = await session.execute(
        text("DELETE FROM event_triggers WHERE id = :id AND workspace_id = :ws"),
        {"id": str(trigger_id), "ws": str(ctx.workspace_id)},
    )
    if res.rowcount == 0:
        raise HTTPException(status_code=404, detail="trigger 不存在")
    return ApiResponse(message="trigger 已刪除")


@router.get("/{trigger_id}/runs", response_model=ApiResponse, summary="列出 trigger 觸發紀錄")
async def list_runs(
    trigger_id: uuid.UUID,
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    rows = await session.execute(
        text(
            """
            SELECT id, fired_at, finished_at, status, output_summary, error,
                   tokens_used, cost_usd
            FROM event_trigger_runs
            WHERE trigger_id = :tid AND workspace_id = :ws
            ORDER BY fired_at DESC
            LIMIT 100
            """
        ),
        {"tid": str(trigger_id), "ws": str(ctx.workspace_id)},
    )
    return ApiResponse(data=[dict(r._mapping) for r in rows.fetchall()])
