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
    # v3.4 P1: non-LLM unit-based metering（image / second / char / call）
    unit_type:         str | None       = None
    unit_count:        float            = 0.0
    # v3.7 P1: per-conversation / per-message cost attribution
    conversation_id:   str | None       = None
    message_id:        str | None       = None
    # v3.7 P2: feature 標籤（chat / workflow / hit_test / embed / image / stt / tts / rerank）
    feature:           str | None       = None


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
                    cost_usd, latency_ms, status, error,
                    unit_type, unit_count,
                    conversation_id, message_id,
                    feature
                ) VALUES (
                    :id, :ws, :uid, :app_id,
                    :ptype, :model,
                    :pt, :ct, :tt,
                    :cost, :latency, :status, :error,
                    :unit_type, :unit_count,
                    :conv_id, :msg_id,
                    :feature
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
                "unit_type":  rec.unit_type,
                "unit_count": rec.unit_count,
                "conv_id":    rec.conversation_id,
                "msg_id":     rec.message_id,
                "feature":    rec.feature,
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


async def get_user_quota(
    session: AsyncSession, workspace_id: str, user_id: str
) -> dict[str, Any]:
    """讀 user 層 quota；無設定回 {None, None}。"""
    r = await session.execute(
        text(
            "SELECT monthly_token_cap, monthly_cost_cap_usd "
            "FROM user_quotas WHERE workspace_id = :ws AND user_id = :uid"
        ),
        {"ws": workspace_id, "uid": user_id},
    )
    row = r.fetchone()
    if not row:
        return {"monthly_token_cap": None, "monthly_cost_cap_usd": None}
    d = dict(row._mapping)
    return {
        "monthly_token_cap":    d.get("monthly_token_cap"),
        "monthly_cost_cap_usd": (
            float(d["monthly_cost_cap_usd"]) if d.get("monthly_cost_cap_usd") is not None else None
        ),
    }


async def get_user_monthly_usage(
    session: AsyncSession, workspace_id: str, user_id: str
) -> dict[str, Any]:
    """取得指定 user 在當月（自然月起算）總 tokens / cost。"""
    r = await session.execute(
        text(
            """
            SELECT
                COALESCE(SUM(total_tokens), 0)::BIGINT AS tokens,
                COALESCE(SUM(cost_usd), 0)::NUMERIC(12, 6) AS cost
            FROM model_usage_logs
            WHERE workspace_id = :ws
              AND user_id = :uid
              AND created_at >= date_trunc('month', now())
            """
        ),
        {"ws": workspace_id, "uid": user_id},
    )
    row = r.fetchone()
    d = dict(row._mapping) if row else {"tokens": 0, "cost": 0}
    return {
        "tokens":   int(d.get("tokens") or 0),
        "cost_usd": float(d.get("cost") or 0),
    }


async def check_quota(
    session: AsyncSession,
    workspace_id: str,
    user_id: str | None = None,
) -> None:
    """超過 cap 時 raise QuotaExceeded；皆未設則直接過。

    v3.3 D1：先檢 workspace 層、再檢 user 層；任一層超額就 raise，
    error message 標記哪一層（workspace / user）以利 UI 區分。
    v5.12：最前面加 trial 凍結 enforce — trial_expiry_worker 標 is_frozen 後一律擋計費操作。
    """
    # ── 0. trial 凍結（v5.12）─────────────────────────────────
    # trial 到期被 trial_expiry_worker 標 is_frozen=TRUE，原本「標了沒人 enforce」→ 到期仍免費用。
    # 在所有計費路徑共同入口（check_quota）擋下：LLM / 媒體 / 檢索消耗一律拒。
    fr = await session.execute(
        text("SELECT is_frozen FROM workspace WHERE id = :ws"), {"ws": workspace_id}
    )
    frow = fr.fetchone()
    if frow is not None and frow.is_frozen:
        raise QuotaExceeded(
            f"[frozen] workspace {workspace_id} 已凍結（trial 到期），請升級方案後繼續使用"
        )

    # ── 1. workspace cap ─────────────────────────────────────
    q = await get_quota(session, workspace_id)
    if q["monthly_token_cap"] is not None or q["monthly_cost_cap_usd"] is not None:
        u = await get_monthly_usage(session, workspace_id)
        if q["monthly_token_cap"] is not None and u["tokens"] >= int(q["monthly_token_cap"]):
            raise QuotaExceeded(
                f"[workspace] workspace {workspace_id} 已達月 token 上限 "
                f"({u['tokens']}/{q['monthly_token_cap']})"
            )
        if q["monthly_cost_cap_usd"] is not None and u["cost_usd"] >= float(q["monthly_cost_cap_usd"]):
            raise QuotaExceeded(
                f"[workspace] workspace {workspace_id} 已達月成本上限 "
                f"(${u['cost_usd']:.2f}/${q['monthly_cost_cap_usd']:.2f})"
            )

    # ── 2. user cap（若有傳 user_id）──────────────────────────
    if not user_id:
        return
    uq = await get_user_quota(session, workspace_id, user_id)
    if uq["monthly_token_cap"] is None and uq["monthly_cost_cap_usd"] is None:
        return
    uu = await get_user_monthly_usage(session, workspace_id, user_id)
    if uq["monthly_token_cap"] is not None and uu["tokens"] >= int(uq["monthly_token_cap"]):
        raise QuotaExceeded(
            f"[user] user {user_id} 已達月 token 上限 "
            f"({uu['tokens']}/{uq['monthly_token_cap']})"
        )
    if uq["monthly_cost_cap_usd"] is not None and uu["cost_usd"] >= float(uq["monthly_cost_cap_usd"]):
        raise QuotaExceeded(
            f"[user] user {user_id} 已達月成本上限 "
            f"(${uu['cost_usd']:.2f}/${uq['monthly_cost_cap_usd']:.2f})"
        )


async def calc_cost(
    session: AsyncSession,
    *,
    model: str | None,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """查 ai_models 取定價算 cost；查不到 / NULL 都回 0.0。"""
    if not model:
        return 0.0
    r = await session.execute(
        text("""
            SELECT price_per_1k_input_usd, price_per_1k_output_usd
            FROM ai_models
            WHERE model_name = :model
            LIMIT 1
        """),
        {"model": model},
    )
    row = r.fetchone()
    if not row:
        return 0.0
    pin = float(row[0] or 0)
    pout = float(row[1] or 0)
    return round((prompt_tokens / 1000.0) * pin + (completion_tokens / 1000.0) * pout, 6)


async def calc_media_cost(
    session: AsyncSession,
    *,
    model: str | None,
    unit_type: str,     # 'image' | 'second' | 'char' | 'call'
    unit_count: float,
) -> float:
    """查 ai_models 取 unit-based 定價算 cost；查不到 / NULL 都回 0.0。

    char 為 per-1k chars，內部會自動 / 1000。
    """
    if not model or unit_count <= 0:
        return 0.0
    col = {
        "image":  "price_per_image_usd",
        "second": "price_per_second_usd",
        "char":   "price_per_1k_chars_usd",  # 注意：char 是 per-1k
        "call":   "price_per_call_usd",
    }.get(unit_type)
    if not col:
        return 0.0
    r = await session.execute(
        text(f"SELECT {col} FROM ai_models WHERE model_name = :model LIMIT 1"),  # noqa: S608 (col 為固定白名單)
        {"model": model},
    )
    row = r.fetchone()
    if not row or row[0] is None:
        return 0.0
    rate = float(row[0])
    if unit_type == "char":
        return round((unit_count / 1000.0) * rate, 6)
    return round(unit_count * rate, 6)
