"""ai_models pricing seed — lifespan 啟動時跑，UPSERT 已知 model 的價格。

只更新 NULL 的欄位（不覆蓋使用者已手動設定的價格）。
"""
import structlog
from sqlalchemy import text
from app.data.model_pricing import MODEL_PRICING

log = structlog.get_logger()


async def seed_model_pricing(session_factory):
    """從 MODEL_PRICING dict UPSERT 進 ai_models 表。"""
    async with session_factory() as session:
        updated = 0
        for model_name, (price_in, price_out) in MODEL_PRICING.items():
            r = await session.execute(
                text("""
                    UPDATE ai_models
                    SET price_per_1k_input_usd  = COALESCE(price_per_1k_input_usd,  :pin),
                        price_per_1k_output_usd = COALESCE(price_per_1k_output_usd, :pout)
                    WHERE model_name = :name
                      AND (price_per_1k_input_usd IS NULL OR price_per_1k_output_usd IS NULL)
                """),
                {"name": model_name, "pin": price_in, "pout": price_out},
            )
            updated += r.rowcount or 0
        await session.commit()
        log.info("model_pricing_seeded", updated=updated, total=len(MODEL_PRICING))

    # v3.4 P1: seed non-LLM media pricing (image/second/char/call)
    async with session_factory() as session:
        from app.data.model_pricing import MEDIA_PRICING
        media_updated = 0
        for model_name, prices in MEDIA_PRICING.items():
            r = await session.execute(
                text("""
                    UPDATE ai_models
                    SET price_per_image_usd     = COALESCE(price_per_image_usd,     :img),
                        price_per_second_usd    = COALESCE(price_per_second_usd,    :sec),
                        price_per_1k_chars_usd  = COALESCE(price_per_1k_chars_usd,  :char1k),
                        price_per_call_usd      = COALESCE(price_per_call_usd,      :call)
                    WHERE model_name = :name
                      AND (price_per_image_usd IS NULL OR price_per_second_usd IS NULL
                           OR price_per_1k_chars_usd IS NULL OR price_per_call_usd IS NULL)
                """),
                {
                    "name": model_name,
                    "img":  prices.get("image"),
                    "sec":  prices.get("second"),
                    "char1k": prices.get("chars_1k"),
                    "call": prices.get("call"),
                },
            )
            media_updated += r.rowcount or 0
        await session.commit()
        log.info("media_pricing_seeded", updated=media_updated, total=len(MEDIA_PRICING))
