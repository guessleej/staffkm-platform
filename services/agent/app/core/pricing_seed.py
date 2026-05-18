"""ai_models pricing seed — lifespan 啟動時跑，UPSERT 已知 model 的價格。

只更新 NULL 的欄位（不覆蓋使用者已手動設定的價格）。
"""
import structlog
from sqlalchemy import text
from app.data.model_pricing import MODEL_PRICING

log = structlog.get_logger()


async def seed_model_pricing(session_factory):
    """v5.0.4: 對既有 provider INSERT default model row（如果還沒有）+ UPSERT pricing。"""
    # 0. 先 seed model row（per provider type）— v5.0.4 修：之前只 UPDATE 不 INSERT 導致 admin/models 空
    async with session_factory() as session:
        from app.data.model_pricing import PROVIDER_DEFAULT_MODELS
        seeded = 0
        # 對每個現有 provider，看它的 type 對應該補哪些 model
        provider_rows = (await session.execute(
            text("SELECT id, provider_type FROM model_providers WHERE status = 'active'")
        )).fetchall()
        for prov in provider_rows:
            defaults = PROVIDER_DEFAULT_MODELS.get(prov.provider_type, [])
            for name, mtype, display in defaults:
                r = await session.execute(text("""
                    INSERT INTO ai_models (provider_id, model_name, model_type, display_name, status, is_default)
                    SELECT CAST(:pid AS uuid), CAST(:n AS varchar), CAST(:t AS varchar), CAST(:d AS varchar), 'active', FALSE
                    WHERE NOT EXISTS (
                        SELECT 1 FROM ai_models
                        WHERE provider_id = CAST(:pid AS uuid) AND model_name = CAST(:n AS varchar)
                    )
                """), {"pid": str(prov.id), "n": name, "t": mtype, "d": display})
                seeded += r.rowcount or 0
        await session.commit()
        if seeded:
            log.info("default_models_seeded", count=seeded, providers=len(provider_rows))

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
