"""ai_models pricing seed — lifespan 啟動時跑，UPSERT 已知 model 的價格。

只更新 NULL 的欄位（不覆蓋使用者已手動設定的價格）。
"""
import structlog
from sqlalchemy import text
from app.data.model_pricing import MODEL_PRICING

log = structlog.get_logger()


async def seed_model_pricing(session_factory):
    """UPSERT 已知 model 的價格（只補 NULL 欄位，不覆蓋使用者已設定的價格）。

    v5.13：**移除**「啟動時 seed 預設 model row」那段——它每次開機從寫死的
    PROVIDER_DEFAULT_MODELS 把幻覺模型（如 azure_openai 的 gpt-4o）INSERT 回 ai_models，
    使用者刪掉後一重啟又復活。模型清單一律由 admin/models 即時動態偵測（ollama /api/tags、
    OpenAI 相容 /v1/models），不再寫死任何 seed。本函式只負責「替既有 model row 補價格」。
    """
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
