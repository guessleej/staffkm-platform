"""LLM call metering — 包 provider.chat() / chat_stream() 以做 quota check + usage record。

設計：context manager + 物件 mutate 的 pattern，避免 BaseProvider 跟 session 耦合。

使用：
    async with meter_llm_call(
        session,
        workspace_id=ws_id,
        user_id=user_id,
        application_id=app_id,
        provider_type="openai",
        model="gpt-4o",
    ) as meter:
        resp = await provider.chat(req)
        meter.record(
            prompt_tokens=resp.prompt_tokens,
            completion_tokens=resp.completion_tokens,
        )
    # context 結束時自動寫 usage log + commit

Streaming 注意：
- async generator 必須被 outer code consume 完，`finally` 才會跑到 record_usage。
- 在 stream 結束 / 完整 collect 完 token 後再呼叫 `meter.record(...)`，
  不要邊串邊 commit。
"""
from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.usage import (
    QuotaExceeded,
    UsageRecord,
    calc_cost,
    calc_media_cost,
    check_quota,
    record_usage,
)

log = structlog.get_logger()


async def _consume_credits(session: AsyncSession, ws: str, cost: float) -> None:
    """v5.12：topup / trial plan 的用量從 credits_balance 扣款（原本只增不減 → 儲值客戶永遠免費）。
    與呼叫端的 usage record **同一交易**（不自行 commit）→ 用量與扣款原子落地，不會「記了用量卻沒扣款」。
    - subscription（starter/pro）由訂閱 cover、metered（usage）由 usage_report_worker 報 Stripe → 皆不扣。
    - balance<0 只 log warning，不做 hard stop（硬性額度走 check_quota）。每筆消費獨立記帳、不去重。
    例外往外傳給呼叫端的 try（與 usage record 一起 rollback，保持原子）。
    """
    if cost is None or cost <= 0:
        return
    r = await session.execute(
        text("SELECT plan FROM billing_accounts WHERE workspace_id = :ws FOR UPDATE"), {"ws": ws}
    )
    row = r.fetchone()
    if not row or row.plan not in ("topup", "trial"):
        return
    r2 = await session.execute(text("""
        UPDATE billing_accounts SET credits_balance = credits_balance - :c, updated_at = now()
        WHERE workspace_id = :ws RETURNING credits_balance
    """), {"c": float(cost), "ws": ws})
    new_bal = float(r2.scalar())
    await session.execute(text("""
        INSERT INTO credit_ledger (workspace_id, delta_usd, reason, reference, balance_after)
        VALUES (:ws, :d, 'consume_usage', NULL, :ba)
    """), {"ws": ws, "d": -float(cost), "ba": new_bal})
    if new_bal < 0:
        log.warning("credits_balance_negative", workspace=ws, balance=new_bal)


class _Meter:
    def __init__(self):
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.error: str | None = None

    def record(self, *, prompt_tokens: int, completion_tokens: int) -> None:
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


@asynccontextmanager
async def meter_llm_call(
    session: AsyncSession,
    *,
    workspace_id: str | uuid.UUID,
    user_id: str | uuid.UUID | None = None,
    application_id: str | uuid.UUID | None = None,
    provider_type: str | None = None,
    model: str | None = None,
    conversation_id: str | uuid.UUID | None = None,
    message_id: str | uuid.UUID | None = None,
    feature: str | None = None,  # v3.7 P2: 'chat' | 'workflow' | 'hit_test' | 'embed' ...
):
    """Pre: check_quota（超額 raise）；post: record_usage（自動算 cost、commit）。

    v3.7 P1：新增 conversation_id / message_id 做 per-conversation cost 歸因。
    v3.7 P2：feature 標籤讓 dashboard 分流。
    """
    ws = str(workspace_id)
    uid = str(user_id) if user_id else None
    # Pre-check：超額直接 raise，caller / FastAPI exception handler 接
    # v3.3 D1：傳 user_id 進去做 user-level cap 檢查
    try:
        await check_quota(session, ws, user_id=uid)
    except QuotaExceeded:
        raise

    start = time.monotonic()
    meter = _Meter()
    status = "ok"
    try:
        yield meter
    except Exception as e:
        status = "error"
        meter.error = str(e)[:500]
        raise
    finally:
        latency_ms = int((time.monotonic() - start) * 1000)
        try:
            cost = await calc_cost(
                session,
                model=model,
                prompt_tokens=meter.prompt_tokens,
                completion_tokens=meter.completion_tokens,
            )
            await record_usage(session, UsageRecord(
                workspace_id=ws,
                user_id=str(user_id) if user_id else None,
                application_id=str(application_id) if application_id else None,
                provider_type=provider_type,
                model=model,
                prompt_tokens=meter.prompt_tokens,
                completion_tokens=meter.completion_tokens,
                total_tokens=meter.prompt_tokens + meter.completion_tokens,
                cost_usd=cost,
                latency_ms=latency_ms,
                status=status,
                error=meter.error,
                conversation_id=str(conversation_id) if conversation_id else None,
                message_id=str(message_id) if message_id else None,
                feature=feature,
            ))
            # v5.12: topup/trial 扣 credits — 與 usage record 同交易（原子）、只在成功時扣
            #   （失敗請求不扣餘額）。任一步出錯 → 整批 rollback、不會出現「記用量沒扣款」。
            if status == "ok":
                await _consume_credits(session, ws, cost)
            await session.commit()
        except Exception as e:
            log.warning("meter_record_failed", workspace=ws, error=str(e))


# ── v3.4 P1: non-LLM media metering ─────────────────────────────────────────
class _MediaMeter:
    """unit-based meter（image / second / char / call）。"""

    def __init__(self):
        self.count: float = 0.0
        self.error: str | None = None

    def record(self, *, unit_count: float) -> None:
        self.count = float(unit_count or 0)


@asynccontextmanager
async def meter_media_call(
    session: AsyncSession,
    *,
    workspace_id: str | uuid.UUID,
    user_id: str | uuid.UUID | None = None,
    application_id: str | uuid.UUID | None = None,
    provider_type: str | None = None,
    model: str | None = None,
    unit_type: str,  # 'image' | 'second' | 'char' | 'call'
    conversation_id: str | uuid.UUID | None = None,
    message_id: str | uuid.UUID | None = None,
    feature: str | None = None,  # v3.7 P2: 'image' | 'stt' | 'tts' | 'rerank'
):
    """Pre: check_quota；post: record_usage 用 unit-based pricing。

    與 meter_llm_call 對稱；非 token-based node（DALL-E / Whisper / TTS / Reranker）使用。
    """
    ws = str(workspace_id)
    uid = str(user_id) if user_id else None
    try:
        await check_quota(session, ws, user_id=uid)
    except QuotaExceeded:
        raise

    start = time.monotonic()
    meter = _MediaMeter()
    status = "ok"
    try:
        yield meter
    except Exception as e:
        status = "error"
        meter.error = str(e)[:500]
        raise
    finally:
        latency_ms = int((time.monotonic() - start) * 1000)
        try:
            cost = await calc_media_cost(
                session, model=model, unit_type=unit_type, unit_count=meter.count,
            )
            await record_usage(session, UsageRecord(
                workspace_id=ws,
                user_id=uid,
                application_id=str(application_id) if application_id else None,
                provider_type=provider_type,
                model=model,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                cost_usd=cost,
                latency_ms=latency_ms,
                status=status,
                error=meter.error,
                unit_type=unit_type,
                unit_count=meter.count,
                conversation_id=str(conversation_id) if conversation_id else None,
                message_id=str(message_id) if message_id else None,
                feature=feature,
            ))
            # v5.12: 與 LLM 對稱 — 同交易、只在成功時扣 media 用量
            if status == "ok":
                await _consume_credits(session, ws, cost)
            await session.commit()
        except Exception as e:
            log.warning("meter_media_record_failed", workspace=ws, error=str(e))
