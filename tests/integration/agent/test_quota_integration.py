"""Quota / 計帳治理路徑的 service 層整合測試（真 PostgreSQL）。

守的是「錢 / 配額」路徑：`app.core.usage` 的 record_usage / get_monthly_usage /
check_quota（雙層：workspace + user）/ calc_cost / calc_media_cost。

這層原本零守護——只有純邏輯單元無法涵蓋：
- asyncpg 對 uuid(str) / numeric / bigint 的 bind 行為
- date_trunc('month', now()) 的自然月邊界 + COALESCE/SUM 聚合
- 雙層 quota 的 raise 時機與訊息標記（[workspace] / [user]）
全部跑真 SQL round-trip。
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.core.usage import (
    QuotaExceeded,
    UsageRecord,
    calc_cost,
    calc_media_cost,
    check_quota,
    get_monthly_usage,
    get_quota,
    get_user_monthly_usage,
    get_user_quota,
    record_usage,
)

pytestmark = pytest.mark.asyncio


def _ws() -> str:
    return str(uuid.uuid4())


async def _set_ws_quota(session, ws, *, token_cap=None, cost_cap=None):
    await session.execute(
        text(
            "INSERT INTO workspace_quotas (workspace_id, monthly_token_cap, monthly_cost_cap_usd) "
            "VALUES (CAST(:ws AS uuid), :tc, :cc)"
        ),
        {"ws": ws, "tc": token_cap, "cc": cost_cap},
    )
    await session.commit()


async def _set_user_quota(session, ws, uid, *, token_cap=None, cost_cap=None):
    await session.execute(
        text(
            "INSERT INTO user_quotas (workspace_id, user_id, monthly_token_cap, monthly_cost_cap_usd) "
            "VALUES (CAST(:ws AS uuid), CAST(:uid AS uuid), :tc, :cc)"
        ),
        {"ws": ws, "uid": uid, "tc": token_cap, "cc": cost_cap},
    )
    await session.commit()


async def _seed_model(session, name, **prices):
    cols = ["model_name"] + list(prices.keys())
    vals = [":model_name"] + [f":{k}" for k in prices]
    await session.execute(
        text(
            f"INSERT INTO ai_models ({', '.join(cols)}) VALUES ({', '.join(vals)})"
        ),
        {"model_name": name, **prices},
    )
    await session.commit()


# ── record_usage + 月聚合 round-trip ─────────────────────────────────────
async def test_record_and_monthly_usage_roundtrip(db_session):
    ws = _ws()
    await record_usage(db_session, UsageRecord(
        workspace_id=ws, prompt_tokens=100, completion_tokens=50, cost_usd=0.012))
    await record_usage(db_session, UsageRecord(
        workspace_id=ws, prompt_tokens=200, completion_tokens=100, cost_usd=0.030))
    await db_session.commit()

    u = await get_monthly_usage(db_session, ws)
    assert u["tokens"] == 450          # (100+50)+(200+100)
    assert round(u["cost_usd"], 3) == 0.042
    assert u["requests"] == 2


async def test_total_tokens_derived_when_zero(db_session):
    """total_tokens 傳 0 → record_usage 用 prompt+completion 補。"""
    ws = _ws()
    await record_usage(db_session, UsageRecord(
        workspace_id=ws, prompt_tokens=30, completion_tokens=70, total_tokens=0))
    await db_session.commit()
    u = await get_monthly_usage(db_session, ws)
    assert u["tokens"] == 100


async def test_monthly_usage_isolated_by_workspace(db_session):
    ws_a, ws_b = _ws(), _ws()
    await record_usage(db_session, UsageRecord(workspace_id=ws_a, prompt_tokens=10, completion_tokens=0))
    await record_usage(db_session, UsageRecord(workspace_id=ws_b, prompt_tokens=999, completion_tokens=0))
    await db_session.commit()
    assert (await get_monthly_usage(db_session, ws_a))["tokens"] == 10


async def test_empty_workspace_zero_usage(db_session):
    u = await get_monthly_usage(db_session, _ws())
    assert u == {"tokens": 0, "cost_usd": 0.0, "requests": 0}


# ── workspace 層 quota ───────────────────────────────────────────────────
async def test_get_quota_none_when_unset(db_session):
    q = await get_quota(db_session, _ws())
    assert q == {"monthly_token_cap": None, "monthly_cost_cap_usd": None}


async def test_check_quota_passes_under_cap(db_session):
    ws = _ws()
    await _set_ws_quota(db_session, ws, token_cap=1000)
    await record_usage(db_session, UsageRecord(workspace_id=ws, prompt_tokens=100, completion_tokens=0))
    await db_session.commit()
    await check_quota(db_session, ws)  # 不 raise


async def test_check_quota_raises_over_token_cap(db_session):
    ws = _ws()
    await _set_ws_quota(db_session, ws, token_cap=100)
    await record_usage(db_session, UsageRecord(workspace_id=ws, prompt_tokens=100, completion_tokens=10))
    await db_session.commit()
    with pytest.raises(QuotaExceeded) as exc:
        await check_quota(db_session, ws)
    assert "[workspace]" in str(exc.value)


async def test_check_quota_raises_over_cost_cap(db_session):
    ws = _ws()
    await _set_ws_quota(db_session, ws, cost_cap="1.00")
    await record_usage(db_session, UsageRecord(workspace_id=ws, cost_usd=1.50))
    await db_session.commit()
    with pytest.raises(QuotaExceeded) as exc:
        await check_quota(db_session, ws)
    assert "成本上限" in str(exc.value)


# ── user 層 quota ────────────────────────────────────────────────────────
async def test_user_quota_layer_raises(db_session):
    ws, uid = _ws(), _ws()
    await _set_ws_quota(db_session, ws, token_cap=10_000)   # workspace 寬鬆
    await _set_user_quota(db_session, ws, uid, token_cap=50)  # user 緊
    await record_usage(db_session, UsageRecord(
        workspace_id=ws, user_id=uid, prompt_tokens=60, completion_tokens=0))
    await db_session.commit()
    with pytest.raises(QuotaExceeded) as exc:
        await check_quota(db_session, ws, user_id=uid)
    assert "[user]" in str(exc.value)


async def test_user_usage_isolated(db_session):
    ws, u1, u2 = _ws(), _ws(), _ws()
    await record_usage(db_session, UsageRecord(workspace_id=ws, user_id=u1, prompt_tokens=10, completion_tokens=0))
    await record_usage(db_session, UsageRecord(workspace_id=ws, user_id=u2, prompt_tokens=70, completion_tokens=0))
    await db_session.commit()
    assert (await get_user_monthly_usage(db_session, ws, u1))["tokens"] == 10
    assert (await get_user_monthly_usage(db_session, ws, u2))["tokens"] == 70


async def test_user_quota_none_when_unset(db_session):
    q = await get_user_quota(db_session, _ws(), _ws())
    assert q == {"monthly_token_cap": None, "monthly_cost_cap_usd": None}


async def test_check_quota_user_cost_cap_raises(db_session):
    ws, uid = _ws(), _ws()
    await _set_user_quota(db_session, ws, uid, cost_cap="0.50")
    await record_usage(db_session, UsageRecord(workspace_id=ws, user_id=uid, cost_usd=0.80))
    await db_session.commit()
    with pytest.raises(QuotaExceeded) as exc:
        await check_quota(db_session, ws, user_id=uid)
    assert "[user]" in str(exc.value)


async def test_check_quota_user_without_own_cap_passes(db_session):
    """有傳 user_id 但該 user 無 quota → user 層直接過（不誤擋）。"""
    ws, uid = _ws(), _ws()
    await record_usage(db_session, UsageRecord(workspace_id=ws, user_id=uid, prompt_tokens=999, completion_tokens=0))
    await db_session.commit()
    await check_quota(db_session, ws, user_id=uid)  # 不 raise


async def test_no_user_id_skips_user_layer(db_session):
    ws = _ws()
    # 沒設任何 cap → check_quota 應直接過（即使有用量）
    await record_usage(db_session, UsageRecord(workspace_id=ws, prompt_tokens=1_000_000, completion_tokens=0))
    await db_session.commit()
    await check_quota(db_session, ws)  # 不 raise


# ── 定價：calc_cost / calc_media_cost ────────────────────────────────────
async def test_calc_cost_from_ai_models(db_session):
    await _seed_model(db_session, "gpt-test",
                      price_per_1k_input_usd="0.0030", price_per_1k_output_usd="0.0060")
    cost = await calc_cost(db_session, model="gpt-test", prompt_tokens=1000, completion_tokens=500)
    # 1000/1k*0.003 + 500/1k*0.006 = 0.003 + 0.003 = 0.006
    assert round(cost, 6) == 0.006


async def test_calc_cost_unknown_model_zero(db_session):
    assert await calc_cost(db_session, model="does-not-exist", prompt_tokens=1000, completion_tokens=0) == 0.0
    assert await calc_cost(db_session, model=None, prompt_tokens=1000, completion_tokens=0) == 0.0


async def test_calc_media_cost_per_unit(db_session):
    await _seed_model(db_session, "img-test", price_per_image_usd="0.040000")
    assert round(await calc_media_cost(db_session, model="img-test", unit_type="image", unit_count=3), 6) == 0.12


async def test_calc_media_cost_char_is_per_1k(db_session):
    await _seed_model(db_session, "tts-test", price_per_1k_chars_usd="0.015000")
    # 2000 chars / 1k * 0.015 = 0.03
    assert round(await calc_media_cost(db_session, model="tts-test", unit_type="char", unit_count=2000), 6) == 0.03


async def test_calc_media_cost_zero_paths(db_session):
    await _seed_model(db_session, "call-test", price_per_call_usd="0.001000")
    assert await calc_media_cost(db_session, model="call-test", unit_type="bogus", unit_count=5) == 0.0
    assert await calc_media_cost(db_session, model="call-test", unit_type="call", unit_count=0) == 0.0
    assert await calc_media_cost(db_session, model=None, unit_type="call", unit_count=5) == 0.0


async def test_calc_media_cost_null_price_zero(db_session):
    """model 存在但該 unit_type 定價為 NULL → 回 0（不爆）。"""
    await _seed_model(db_session, "img-noprice", price_per_call_usd="0.001000")  # 只設 call，image 為 NULL
    assert await calc_media_cost(db_session, model="img-noprice", unit_type="image", unit_count=2) == 0.0


async def test_record_usage_swallows_bad_insert(db_session):
    """record_usage 內建 try/except → 壞資料不該往上炸（計帳失敗不可阻斷主流程）。"""
    # workspace_id 非合法 uuid → INSERT 會炸，但 record_usage 應吞掉只 warning
    await record_usage(db_session, UsageRecord(workspace_id="not-a-uuid", prompt_tokens=1))
    # 不 raise 即通過
