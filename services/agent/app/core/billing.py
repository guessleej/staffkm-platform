"""Stripe billing helpers — v4.7+v4.8 G+H.

Lazy-import stripe SDK 以避免無 STRIPE_SECRET_KEY 環境炸 import。
所有 DB 操作 idempotent；webhook + topup 用 stripe object id 當 reference。
"""
from __future__ import annotations
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

log = structlog.get_logger()


def _stripe():
    """Lazy import stripe (才不會在 no-stripe env 噴錯)。"""
    import stripe  # type: ignore
    if not settings.STRIPE_SECRET_KEY:
        raise RuntimeError("STRIPE_SECRET_KEY not configured")
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


async def get_or_create_customer(session: AsyncSession, workspace_id: str, email: str) -> str:
    """確保 workspace 有 Stripe customer，回 customer_id。"""
    r = await session.execute(text("""
        SELECT stripe_customer_id FROM billing_accounts WHERE workspace_id = :ws
    """), {"ws": workspace_id})
    row = r.fetchone()
    if row and row.stripe_customer_id:
        return row.stripe_customer_id

    stripe = _stripe()
    customer = stripe.Customer.create(
        email=email,
        metadata={"workspace_id": workspace_id},
    )

    # upsert
    await session.execute(text("""
        INSERT INTO billing_accounts (workspace_id, stripe_customer_id, plan, status)
        VALUES (:ws, :cid, 'trial', 'active')
        ON CONFLICT (workspace_id) DO UPDATE
        SET stripe_customer_id = EXCLUDED.stripe_customer_id, updated_at = now()
    """), {"ws": workspace_id, "cid": customer.id})
    await session.commit()
    return customer.id


async def create_checkout_session(workspace_id: str, customer_id: str, plan: str) -> str:
    """建 Checkout session（plan: starter|pro|usage|topup10|topup50|topup200）。回 checkout url。"""
    stripe = _stripe()

    price_map = {
        "starter": settings.STRIPE_PRICE_STARTER,
        "pro":     settings.STRIPE_PRICE_PRO,
        "usage":   settings.STRIPE_PRICE_USAGE,
    }

    if plan in ("starter", "pro", "usage"):
        price_id = price_map[plan]
        if not price_id:
            raise ValueError(f"STRIPE_PRICE for plan '{plan}' not configured")
        mode = "subscription"
        sess = stripe.checkout.Session.create(
            customer=customer_id,
            mode=mode,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{settings.BILLING_PUBLIC_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.BILLING_PUBLIC_URL}/billing/cancel",
            metadata={"workspace_id": workspace_id, "plan": plan},
        )
        return sess.url

    if plan.startswith("topup"):
        # pre-paid credits one-time payment
        try:
            usd = int(plan[5:])
        except ValueError:
            raise ValueError(f"invalid topup plan: {plan}")
        amount = usd * 100  # USD cents
        sess = stripe.checkout.Session.create(
            customer=customer_id,
            mode="payment",
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": f"staffKM credits topup ${usd}"},
                    "unit_amount": amount,
                },
                "quantity": 1,
            }],
            success_url=f"{settings.BILLING_PUBLIC_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.BILLING_PUBLIC_URL}/billing/cancel",
            metadata={"workspace_id": workspace_id, "plan": plan, "topup_usd": str(usd)},
        )
        return sess.url

    raise ValueError(f"unknown plan: {plan}")


async def add_credits(session: AsyncSession, workspace_id: str, delta_usd: float,
                      reason: str, reference: str | None = None) -> float:
    """Update billing_accounts.credits_balance + write ledger entry. Returns new balance."""
    r = await session.execute(text("""
        SELECT credits_balance FROM billing_accounts WHERE workspace_id = :ws
        FOR UPDATE
    """), {"ws": workspace_id})
    row = r.fetchone()
    current = float(row.credits_balance) if row else 0.0

    # v5.12: reference 去重 — Stripe webhook 是 at-least-once，重送同一 topup（或我方回 500 後
    # Stripe 重試）不可重複加值。FOR UPDATE 鎖 billing_accounts（同 ws 序列化），在鎖內查 ledger；
    # 同 reference 必同 ws → 第二筆並發會等前者 commit 後查到、直接跳過。reference 為 None
    # （手動調整 / 消費扣款）不去重。另有 backstop partial unique index（init.sql）防 row 不存在的競態。
    if reference:
        dup = await session.execute(text("""
            SELECT balance_after FROM credit_ledger WHERE reference = :ref LIMIT 1
        """), {"ref": reference})
        drow = dup.fetchone()
        if drow is not None:
            await session.commit()  # 釋放 FOR UPDATE 鎖
            log.info("add_credits_duplicate_skipped", ws=workspace_id, reference=reference)
            return float(drow.balance_after)

    new_balance = current + delta_usd

    from sqlalchemy.exc import IntegrityError
    try:
        if row:
            await session.execute(text("""
                UPDATE billing_accounts SET credits_balance = :b, updated_at = now()
                WHERE workspace_id = :ws
            """), {"b": new_balance, "ws": workspace_id})
        else:
            await session.execute(text("""
                INSERT INTO billing_accounts (workspace_id, credits_balance, plan, status)
                VALUES (:ws, :b, 'trial', 'active')
            """), {"ws": workspace_id, "b": new_balance})

        await session.execute(text("""
            INSERT INTO credit_ledger (workspace_id, delta_usd, reason, reference, balance_after)
            VALUES (:ws, :d, :r, :ref, :ba)
        """), {"ws": workspace_id, "d": delta_usd, "r": reason, "ref": reference, "ba": new_balance})
        await session.commit()
        return new_balance
    except IntegrityError:
        # v5.12: 並發首次 topup（billing_accounts row 不存在 → FOR UPDATE 鎖不到、兩者都 miss
        #   去重 SELECT）→ 兩筆都 INSERT 同 reference，第二筆撞 uq_credit_ledger_reference。
        #   視為「已處理」：rollback + 回已寫入的 balance，不重複加值、也不讓 webhook 收 500
        #   （避免 Stripe at-least-once 重試風暴）。
        await session.rollback()
        if reference:
            dup = await session.execute(text(
                "SELECT balance_after FROM credit_ledger WHERE reference = :ref LIMIT 1"
            ), {"ref": reference})
            drow = dup.fetchone()
            if drow is not None:
                log.info("add_credits_unique_conflict_skipped", ws=workspace_id, reference=reference)
                return float(drow.balance_after)
        raise  # 非 reference 去重衝突 → 真錯誤，往外傳


async def report_usage_to_stripe(
    session: AsyncSession,
    workspace_id: str,
    period_start: Any,
    period_end: Any,
    tokens: int,
    cost_usd: float,
) -> None:
    """v4.8 H / v5.12: 把當期 usage 透過 Stripe Usage Records API 回報。

    記錄到 usage_reports 表（unique key 防重送）。v5.12 補上真實 Stripe API 呼叫
    （取 subscription 的 item → create_usage_record）。未設 Stripe / 無 subscription 時
    僅記本地、不致命。⚠ 真實 metered 計費需在有 Stripe key + metered price 的環境端對端驗證。
    """
    # idempotent check
    r = await session.execute(text("""
        SELECT id FROM usage_reports
        WHERE workspace_id = :ws AND period_start = :s AND period_end = :e
    """), {"ws": workspace_id, "s": period_start, "e": period_end})
    if r.fetchone():
        log.info("usage_already_reported", ws=workspace_id, period=str(period_start))
        return

    # v5.12: 真實 Stripe usage record — 取 ws 的 subscription_item 後 increment quantity=tokens。
    event_id: str | None = None
    try:
        stripe = _stripe()  # 未設 STRIPE_SECRET_KEY 會 raise → except 記錄、僅本地存
        acct = await session.execute(text("""
            SELECT stripe_subscription_id FROM billing_accounts WHERE workspace_id = :ws
        """), {"ws": workspace_id})
        arow = acct.fetchone()
        sub_id = getattr(arow, "stripe_subscription_id", None) if arow else None
        if not sub_id:
            log.info("usage_report_no_subscription", ws=workspace_id, tokens=tokens)
        else:
            sub = stripe.Subscription.retrieve(sub_id)
            items = (sub.get("items", {}) or {}).get("data", [])
            if not items:
                log.warning("usage_report_no_sub_item", ws=workspace_id, sub=sub_id)
            else:
                rec = stripe.SubscriptionItem.create_usage_record(
                    items[0]["id"], quantity=int(tokens), action="increment",
                )
                event_id = rec.get("id")
                log.info("usage_report_stripe_ok",
                         ws=workspace_id, tokens=tokens, usage_record=event_id)
    except Exception as e:
        log.warning("stripe_usage_report_failed", error=str(e))

    await session.execute(text("""
        INSERT INTO usage_reports (workspace_id, period_start, period_end,
                                   tokens_reported, cost_reported_usd, stripe_event_id)
        VALUES (:ws, :s, :e, :tk, :c, :eid)
    """), {"ws": workspace_id, "s": period_start, "e": period_end,
           "tk": tokens, "c": cost_usd, "eid": event_id})
    await session.commit()
