"""Celery 背景任務：embedding 熱換 — 全庫重嵌 +（維度不符時）遷移共用 vector 欄。

由 admin 端點 POST /knowledge/embedding/reindex 觸發。解析目標 embedding 模型所屬
provider 的 base_url/api_key（ollama 補 /v1），再交給 core.reindex.reindex_embeddings。
"""
import asyncio
import base64
import datetime
import json

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.core.reindex import PROGRESS_KEY, reindex_embeddings
from app.tasks.celery_app import celery_app

log = structlog.get_logger()


async def _resolve_provider(session, model_name: str) -> tuple[str | None, str]:
    """由 model_name 找 embedding 模型的 provider base_url(+/v1)/api_key；查無回 env。"""
    row = (await session.execute(
        text("""
            SELECT p.base_url, p.api_key_enc FROM ai_models m
            JOIN model_providers p ON p.id = m.provider_id
            WHERE m.model_name = :mn AND m.model_type = 'embedding' AND m.status = 'active'
            ORDER BY m.is_default DESC LIMIT 1
        """),
        {"mn": model_name},
    )).fetchone()
    if not row:
        return (settings.EMBEDDING_BASE_URL or None, settings.OPENAI_API_KEY)
    base = row.base_url
    if base and not base.rstrip("/").endswith("/v1"):  # ollama 原生 → 補 /v1（embeddings 走 OpenAI 相容）
        base = base.rstrip("/") + "/v1"
    key = settings.OPENAI_API_KEY
    if row.api_key_enc:
        try:
            key = base64.b64decode(row.api_key_enc.encode()).decode()
        except Exception:  # noqa: BLE001
            pass
    return (base, key)


@celery_app.task(bind=True, name="app.tasks.reindex_embeddings.reindex", acks_late=True)
def reindex(self, model_name: str) -> dict:
    return asyncio.run(_run(model_name))


async def _run(model_name: str) -> dict:
    engine = create_async_engine(settings.DB_URL, pool_size=1, max_overflow=0)
    sf = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sf() as session:
            base_url, api_key = await _resolve_provider(session, model_name)
            return await reindex_embeddings(session, model_name, api_key or "dummy", base_url)
    except Exception as exc:  # noqa: BLE001 — 標記失敗進度，方便前端顯示
        log.error("reindex_failed", model=model_name, error=str(exc)[:300])
        try:
            async with sf() as s2:
                await s2.execute(
                    text("""
                        INSERT INTO system_settings (key, value, updated_at)
                        VALUES (:k, CAST(:v AS jsonb), now())
                        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()
                    """),
                    {"k": PROGRESS_KEY, "v": json.dumps({
                        "status": "error", "model": model_name, "error": str(exc)[:300],
                        "at": datetime.datetime.utcnow().isoformat(),
                    })},
                )
                await s2.commit()
        except Exception:  # noqa: BLE001
            pass
        raise
    finally:
        await engine.dispose()
