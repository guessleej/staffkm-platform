"""Quota 並發扣減競態 — meter_llm_call 的 check→record 原子性特性（真 PostgreSQL）。

meter_llm_call 是「pre-check_quota → yield → post-record_usage」：**check 與 record 之間
沒有原子保留（reservation）**，是經典 TOCTOU。本檔用真 DB + 各自獨立 session（鏡像
production 每 request 一條連線）把並發行為**如實刻畫**，而非假裝它是 hard cap：

1. 並發 record **不丟寫**（append-only log，每筆 INSERT 都落 → 帳不會少算）。
2. 循序超額**確實擋**（cap 的契約：記滿後下一筆 raise QuotaExceeded）。
3. **TOCTOU soft-cap**：兩條在「未滿」時各自 check 都過 → 都 record → 總和可**超過 cap**
   （in-flight 並發可超發）；之後新 check 即擋。← 這是已知特性，不是 bug；要 hard cap
   需 atomic reserve（SELECT FOR UPDATE / UPDATE ... WHERE used+delta<=cap），屬設計變更。

誠實標註：token 軟上限對多數場景可接受（事後對帳 + 擋下一筆）；若要 hard 限額（如付費
credits）才需把 quota 改成原子保留——本檔把現況釘住，避免無意間以為它是 hard cap。
"""
from __future__ import annotations

import asyncio
import uuid

import pytest
from sqlalchemy import text

from app.core.metering import meter_llm_call
from app.core.usage import QuotaExceeded, UsageRecord, check_quota, get_monthly_usage, record_usage
from staffkm_core.utils import database as _db

pytestmark = pytest.mark.asyncio


def _ws() -> str:
    return str(uuid.uuid4())


async def _set_cap(session, ws, cap):
    await session.execute(text(
        "INSERT INTO workspace_quotas (workspace_id, monthly_token_cap) "
        "VALUES (CAST(:ws AS uuid), :c)"), {"ws": ws, "c": cap})
    await session.commit()


async def _prefill(session, ws, tokens):
    await session.execute(text(
        "INSERT INTO model_usage_logs (id, workspace_id, total_tokens, created_at) "
        "VALUES (gen_random_uuid(), CAST(:ws AS uuid), :t, now())"), {"ws": ws, "t": tokens})
    await session.commit()


async def _meter_call(ws, tokens) -> str:
    """一次完整 meter_llm_call（各自獨立 session，鏡像 production 每 request 一條連線）。"""
    async with _db._session_factory() as s:
        try:
            async with meter_llm_call(s, workspace_id=ws, provider_type="openai", model=None) as m:
                m.record(prompt_tokens=tokens, completion_tokens=0)
            return "ok"
        except QuotaExceeded:
            return "blocked"


# ── 並發 record 不丟寫（append-only log 安全）─────────────────────────────
async def test_concurrent_records_no_lost_writes(db_session):
    ws = _ws()  # 無 cap → check 一律過；驗 10 條並發 record 都落、總和正確
    results = await asyncio.gather(*(_meter_call(ws, 5) for _ in range(10)))
    assert results == ["ok"] * 10

    rows = (await db_session.execute(text(
        "SELECT count(*), COALESCE(SUM(total_tokens),0) FROM model_usage_logs "
        "WHERE workspace_id = CAST(:ws AS uuid)"), {"ws": ws})).one()
    assert rows[0] == 10            # 10 筆都在（無 lost update）
    assert rows[1] == 50            # 10 × 5 tokens


# ── 循序超額確實擋（cap 契約）──────────────────────────────────────────────
async def test_sequential_over_cap_blocks(db_session):
    ws = _ws()
    await _set_cap(db_session, ws, 100)
    assert await _meter_call(ws, 100) == "ok"      # 記滿 100
    assert await _meter_call(ws, 10) == "blocked"  # 下一筆：已達上限 → 擋


# ── TOCTOU soft-cap：未滿時並發 check 都過 → 可超發 ────────────────────────
async def test_toctou_soft_cap_overshoot_then_blocks(db_session):
    ws = _ws()
    await _set_cap(db_session, ws, 100)
    await _prefill(db_session, ws, 90)   # 90/100

    # 兩條獨立 session 在「都還沒 record」時各自 check → 都看到 90 < 100 → 都過
    async with _db._session_factory() as s1, _db._session_factory() as s2:
        await check_quota(s1, ws)        # 不 raise
        await check_quota(s2, ws)        # 不 raise（neither 已 record）
        await record_usage(s1, UsageRecord(workspace_id=ws, prompt_tokens=20, completion_tokens=0))
        await s1.commit()
        await record_usage(s2, UsageRecord(workspace_id=ws, prompt_tokens=20, completion_tokens=0))
        await s2.commit()

    total = (await get_monthly_usage(db_session, ws))["tokens"]
    assert total == 130              # 90 + 20 + 20 → **超過 cap 100**（soft cap，in-flight 可超發）

    # 但超發後，新的 check 立即擋（cap 仍最終生效）
    async with _db._session_factory() as s3:
        with pytest.raises(QuotaExceeded):
            await check_quota(s3, ws)
