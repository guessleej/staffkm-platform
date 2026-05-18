"""Billing endpoints — v4.7+v4.8 G+H.

- GET  /billing/me                 — current plan + credits balance + recent invoices
- POST /billing/checkout            — start Stripe checkout (subscribe / topup)
- POST /billing/portal              — Stripe customer portal session
- POST /billing/webhooks/stripe     — Stripe webhook receiver
- GET  /billing/invoices            — list invoices for current workspace
- GET  /billing/credits/ledger      — credit transactions
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.billing import (
    get_or_create_customer, create_checkout_session, add_credits,
)
from staffkm_core.schemas.response import ApiResponse
from staffkm_core.utils.database import get_session
from staffkm_tenant import TenantContext, require_admin, require_member

router = APIRouter()


# ── workspace-scoped endpoints ────────────────────────────────────────
@router.get("/me", response_model=ApiResponse, summary="Current billing status")
async def me(
    ctx: TenantContext = Depends(require_member),
    session: AsyncSession = Depends(get_session),
):
    r = await session.execute(text("""
        SELECT plan, status, credits_balance, current_period_start, current_period_end
        FROM billing_accounts WHERE workspace_id = :ws
    """), {"ws": str(ctx.workspace_id)})
    row = r.fetchone()
    if not row:
        return ApiResponse(data={
            "plan": "trial", "status": "active",
            "credits_balance": 0.0,
            "current_period_start": None, "current_period_end": None,
        })
    return ApiResponse(data={
        "plan": row.plan, "status": row.status,
        "credits_balance": float(row.credits_balance or 0),
        "current_period_start": row.current_period_start,
        "current_period_end": row.current_period_end,
    })


class CheckoutRequest(BaseModel):
    plan: str  # starter | pro | usage | topup10 | topup50 | topup200


@router.post("/checkout", response_model=ApiResponse, summary="Start Stripe checkout")
async def checkout(
    body: CheckoutRequest,
    ctx: TenantContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(503, "billing not configured")

    # 取 user email
    r = await session.execute(text("""
        SELECT u.email FROM users u
        JOIN workspace_member wm ON wm.user_id = u.id
        WHERE wm.workspace_id = :ws AND u.id = :uid
    """), {"ws": str(ctx.workspace_id), "uid": str(ctx.user_id)})
    row = r.fetchone()
    email = row.email if row else f"workspace-{ctx.workspace_id}@staffkm.local"

    customer_id = await get_or_create_customer(session, str(ctx.workspace_id), email)

    try:
        url = await create_checkout_session(str(ctx.workspace_id), customer_id, body.plan)
        return ApiResponse(data={"checkout_url": url})
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(502, f"stripe error: {e}")


@router.post("/portal", response_model=ApiResponse, summary="Stripe customer portal session")
async def portal(
    ctx: TenantContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(503, "billing not configured")
    r = await session.execute(text("""
        SELECT stripe_customer_id FROM billing_accounts WHERE workspace_id = :ws
    """), {"ws": str(ctx.workspace_id)})
    row = r.fetchone()
    if not row or not row.stripe_customer_id:
        raise HTTPException(400, "no stripe customer; subscribe first")

    try:
        from app.core.billing import _stripe
        stripe = _stripe()
        sess = stripe.billing_portal.Session.create(
            customer=row.stripe_customer_id,
            return_url=f"{settings.BILLING_PUBLIC_URL}/billing",
        )
        return ApiResponse(data={"portal_url": sess.url})
    except Exception as e:
        raise HTTPException(502, f"stripe error: {e}")


@router.get("/invoices", response_model=ApiResponse, summary="List workspace invoices")
async def list_invoices(
    ctx: TenantContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    r = await session.execute(text("""
        SELECT id, stripe_invoice_id, amount_usd, currency, status,
               period_start, period_end, invoice_pdf_url, created_at
        FROM billing_invoices WHERE workspace_id = :ws
        ORDER BY created_at DESC LIMIT 50
    """), {"ws": str(ctx.workspace_id)})
    items = []
    for row in r.fetchall():
        d = dict(row._mapping)
        if d.get("amount_usd") is not None:
            d["amount_usd"] = float(d["amount_usd"])
        items.append(d)
    return ApiResponse(data={"items": items})


@router.get("/credits/ledger", response_model=ApiResponse, summary="Credit transaction log")
async def credit_ledger(
    ctx: TenantContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    r = await session.execute(text("""
        SELECT delta_usd, reason, reference, balance_after, created_at
        FROM credit_ledger WHERE workspace_id = :ws
        ORDER BY created_at DESC LIMIT 100
    """), {"ws": str(ctx.workspace_id)})
    items = []
    for row in r.fetchall():
        d = dict(row._mapping)
        d["delta_usd"] = float(d["delta_usd"])
        d["balance_after"] = float(d["balance_after"])
        items.append(d)
    return ApiResponse(data={"items": items})


# ── public webhook（不走 workspace 前綴；走 /api/v1/public/billing/）─────
@router.post("/webhooks/stripe", summary="Stripe webhook receiver")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
    session: AsyncSession = Depends(get_session),
):
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(503, "webhook not configured")

    payload = await request.body()
    try:
        from app.core.billing import _stripe
        stripe = _stripe()
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        raise HTTPException(400, f"invalid signature: {e}")

    event_type = event["type"]
    obj = event["data"]["object"]

    if event_type == "checkout.session.completed":
        ws_id = obj.get("metadata", {}).get("workspace_id")
        plan = obj.get("metadata", {}).get("plan", "")
        if ws_id and plan.startswith("topup"):
            topup_usd = float(obj.get("metadata", {}).get("topup_usd", 0))
            await add_credits(session, ws_id, topup_usd, "topup_stripe", obj["id"])
        elif ws_id and plan in ("starter", "pro", "usage"):
            await session.execute(text("""
                UPDATE billing_accounts SET plan=:p, status='active', updated_at=now()
                WHERE workspace_id = :ws
            """), {"p": plan, "ws": ws_id})
            await session.commit()

    elif event_type in ("invoice.finalized", "invoice.paid"):
        ws_id = None
        cust_id = obj.get("customer")
        if cust_id:
            r = await session.execute(text("""
                SELECT workspace_id FROM billing_accounts WHERE stripe_customer_id = :c
            """), {"c": cust_id})
            row = r.fetchone()
            if row:
                ws_id = str(row.workspace_id)

        if ws_id:
            await session.execute(text("""
                INSERT INTO billing_invoices (workspace_id, stripe_invoice_id, amount_usd,
                    currency, status, period_start, period_end, invoice_pdf_url)
                VALUES (:ws, :id, :amt, :cur, :st, to_timestamp(:ps), to_timestamp(:pe), :pdf)
                ON CONFLICT (stripe_invoice_id) DO UPDATE
                SET status = EXCLUDED.status, invoice_pdf_url = EXCLUDED.invoice_pdf_url
            """), {
                "ws": ws_id,
                "id": obj["id"],
                "amt": float(obj.get("amount_paid", 0)) / 100,
                "cur": obj.get("currency", "usd"),
                "st": obj.get("status", ""),
                "ps": obj.get("period_start") or 0,
                "pe": obj.get("period_end") or 0,
                "pdf": obj.get("invoice_pdf"),
            })
            await session.commit()

    elif event_type in ("customer.subscription.updated", "customer.subscription.deleted"):
        cust_id = obj.get("customer")
        if cust_id:
            new_status = "active" if obj.get("status") == "active" else "canceled"
            await session.execute(text("""
                UPDATE billing_accounts SET status=:s,
                    current_period_start=to_timestamp(:ps),
                    current_period_end=to_timestamp(:pe),
                    updated_at=now()
                WHERE stripe_customer_id = :c
            """), {
                "s": new_status,
                "ps": obj.get("current_period_start") or 0,
                "pe": obj.get("current_period_end") or 0,
                "c": cust_id,
            })
            await session.commit()

    return {"received": True}
