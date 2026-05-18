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
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.usage import (
    QuotaExceeded,
    UsageRecord,
    calc_cost,
    check_quota,
    record_usage,
)

log = structlog.get_logger()


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
):
    """Pre: check_quota（超額 raise）；post: record_usage（自動算 cost、commit）。"""
    ws = str(workspace_id)
    # Pre-check：超額直接 raise，caller / FastAPI exception handler 接
    try:
        await check_quota(session, ws)
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
            ))
            await session.commit()
        except Exception as e:
            log.warning("meter_record_failed", workspace=ws, error=str(e))
