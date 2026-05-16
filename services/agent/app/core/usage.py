"""Token 計帳 + Quota 助手（M3 中段-D）。

提供：
- record_usage()      — 寫一筆 model_usage_logs
- get_monthly_usage() — 取得指定 workspace 當月總 token / cost
- check_quota()       — 檢查 workspace quota；超額 raise QuotaExceeded

目前不直接綁定 BaseProvider；由 caller（application_agent / workflow executor）
在 chat() 完成後手動呼叫 record_usage()。M3 收尾再考慮裝飾器或上下文管理器。
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger()


class QuotaExceeded(Exception):
    """Workspace 已用滿月配額。"""


@dataclass
class UsageRecord:
    workspace_id:      str
    user_id:           str | None       = None
    application_id:    str | None       = None
    provider_type:     str | None       = None
    model:             str | None       = None
    prompt_tokens:     int              = 0
    completion_tokens: int              = 0
    total_tokens:      int              = 0
    cost_usd:          float            = 0.0
    latency_ms:        int              = 0
    status:            str              = "ok"
    error:             str | None       = None


async def record_usage(session: AsyncSession, rec: UsageRecord) -> None:
    """寫一筆 usage log（commit 由 caller 決定）。"""
    try:
        await session.execute(
            text(
                """
                INSERT INTO model_usage_logs (
                    id, workspace_id, user_id, application_id,
                    provider_type, model,
                    prompt_tokens, completion_tokens, total_tokens,
                    cost_usd, latency_ms, status, error
                ) VALUES (
                    :id, :ws, :uid, :app_id,
                    :ptype, :model,
                    :pt, :ct, :tt,
                    :cost, :latency, :status, :error
                )
                """
            ),
            {
                "id":      str(uuid.uuid4()),
                "ws":      rec.workspace_id,
                "uid":     rec.user_id,
                "app_id":  rec.application_id,
                "ptype":   rec.provider_type,
                "model":   rec.model,
                "pt":      rec.prompt_tokens,
                "ct":      rec.completion_tokens,
                "tt":      rec.total_tokens or (rec.prompt_tokens + rec.completion_tokens),
                "cost":    rec.cost_usd,
                "latency": rec.latency_ms,
                "status":  rec.status,
                "error":   rec.error,
            },
        )
    except Exception as e:
        log.warning("usage_record_failed", workspace=rec.workspace_id, error=str(e))


async def get_monthly_usage(session: AsyncSession, workspace_id: str) -> dict[str, Any]:
    """取得當月（自然月起算）總 tokens / cost / 請求數。"""
    r = await session.execute(
        text(
            """
            SELECT
                COALESCE(SUM(total_tokens), 0)::BIGINT AS tokens,
                COALESCE(SUM(cost_usd), 0)::NUMERIC(12, 6) AS cost,
                COUNT(*)::BIGINT AS requests
            FROM model_usage_logs
            WHERE workspace_id = :ws
              AND created_at >= date_trunc('month', now())
            """
        ),
        {"ws": workspace_id},
    )
    row = r.fetchone()
    d = dict(row._mapping) if row else {"tokens": 0, "cost": 0, "requests": 0}
    return {
        "tokens":   int(d.get("tokens") or 0),
        "cost_usd": float(d.get("cost") or 0),
        "requests": int(d.get("requests") or 0),
    }


async def get_quota(session: AsyncSession, workspace_id: str) -> dict[str, Any]:
    r = await session.execute(
        text(
            "SELECT monthly_token_cap, monthly_cost_cap_usd "
            "FROM workspace_quotas WHERE workspace_id = :ws"
        ),
        {"ws": workspace_id},
    )
    row = r.fetchone()
    if not row:
        return {"monthly_token_cap": None, "monthly_cost_cap_usd": None}
    d = dict(row._mapping)
    return {
        "monthly_token_cap":     d.get("monthly_token_cap"),
        "monthly_cost_cap_usd":  (
            float(d["monthly_cost_cap_usd"]) if d.get("monthly_cost_cap_usd") is not None else None
        ),
    }


async def check_quota(session: AsyncSession, workspace_id: str) -> None:
    """超過 cap 時 raise QuotaExceeded；皆未設則直接過。"""
    q = await get_quota(session, workspace_id)
    if q["monthly_token_cap"] is None and q["monthly_cost_cap_usd"] is None:
        return
    u = await get_monthly_usage(session, workspace_id)
    if q["monthly_token_cap"] is not None and u["tokens"] >= int(q["monthly_token_cap"]):
        raise QuotaExceeded(
            f"workspace {workspace_id} 已達月 token 上限 "
            f"({u['tokens']}/{q['monthly_token_cap']})"
        )
    if q["monthly_cost_cap_usd"] is not None and u["cost_usd"] >= float(q["monthly_cost_cap_usd"]):
        raise QuotaExceeded(
            f"workspace {workspace_id} 已達月成本上限 "
            f"(${u['cost_usd']:.2f}/${q['monthly_cost_cap_usd']:.2f})"
        )
