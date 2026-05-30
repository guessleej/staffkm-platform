"""Embedding 熱換：全庫重嵌 +（維度不符時）遷移共用 vector 欄。

⚠ 系統級操作：影響所有 KB/workspace 的向量。維度變更會 DROP index → ALTER 兩個共用
vector 欄（paragraph_embeddings + kb_entities）TYPE vector(N) USING NULL（清掉舊向量）→
全庫重嵌 → 重建 ivfflat index。期間搜尋退化（向量空），重嵌完恢復。重嵌期間請勿 ingest。

流程：UI 存 default.embedding（desired）→ admin 觸發本流程 → 成功後寫 embedding.active
（model/base_url/api_key/dim）→ runtime 的 resolve_embedding 起用新模型（query 與索引一致）。
進度寫 system_settings 'embedding.reindex'。
"""
from __future__ import annotations

import datetime
import json

import structlog
from sqlalchemy import text

from app.config import settings
from app.core.embedder import get_embedder
from app.core.vectorstore import upsert_embedding
from staffkm_core.secrets import encrypt_secret

log = structlog.get_logger()

PROGRESS_KEY = "embedding.reindex"
ACTIVE_KEY = "embedding.active"
_BATCH = 64


async def _set_setting(session, key: str, value: dict) -> None:
    await session.execute(
        text("""
            INSERT INTO system_settings (key, value, updated_at)
            VALUES (:k, CAST(:v AS jsonb), now())
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()
        """),
        {"k": key, "v": json.dumps(value, ensure_ascii=False)},
    )
    await session.commit()


async def probe_dim(model: str, api_key: str, base_url: str | None) -> int:
    """嵌一個探針字串取維度。"""
    v = await get_embedder(model, api_key, base_url).embed_text("dimension probe 維度偵測")
    return len(v)


async def _current_column_dim(session) -> int:
    """讀 paragraph_embeddings.embedding 的 vector 維度（pgvector 的 atttypmod 即維度）。"""
    cur = (await session.execute(text(
        "SELECT atttypmod FROM pg_attribute "
        "WHERE attrelid = 'paragraph_embeddings'::regclass AND attname = 'embedding'"
    ))).scalar()
    return int(cur) if cur and int(cur) > 0 else int(settings.EMBEDDING_DIMENSION)


async def reindex_embeddings(session, model: str, api_key: str, base_url: str | None) -> dict:
    """全庫重嵌（必要時遷移維度）。回 {status, total, done, dim, migrated}。"""
    started = datetime.datetime.utcnow().isoformat()
    target_dim = await probe_dim(model, api_key, base_url)
    cur_dim = await _current_column_dim(session)
    total = (await session.execute(text("SELECT count(*) FROM paragraphs WHERE is_active"))).scalar() or 0
    await _set_setting(session, PROGRESS_KEY, {
        "status": "running", "model": model, "target_dim": target_dim, "cur_dim": cur_dim,
        "total": total, "done": 0, "migrated": False, "started_at": started,
    })
    log.info("reindex_start", model=model, target_dim=target_dim, cur_dim=cur_dim, total=total)

    migrated = False
    if target_dim != cur_dim:
        # 維度遷移：兩個共用 vector 欄一起 ALTER（kb_entities 也用 vector，否則圖錨定壞）
        for stmt in (
            "DROP INDEX IF EXISTS idx_para_embed_vector",
            "DROP INDEX IF EXISTS ix_kb_entities_vec",
            f"ALTER TABLE paragraph_embeddings ALTER COLUMN embedding TYPE vector({target_dim}) USING NULL::vector({target_dim})",
            f"ALTER TABLE kb_entities ALTER COLUMN embedding TYPE vector({target_dim}) USING NULL::vector({target_dim})",
        ):
            await session.execute(text(stmt))
        await session.commit()
        migrated = True
        log.info("reindex_migrated_columns", target_dim=target_dim)

    # 重嵌前先把 active 切到目標模型 → runtime query/ingest 與「已遷移的欄位維度」一致，
    # 重嵌期間頂多回空結果（向量尚未填），不會 1024-query vs 768-column 的硬維度錯誤。
    # v5.12：api_key 加密存（雲端 embedding key 不可明文落 DB / 進備份）。resolve_embedding 解密讀。
    await _set_setting(session, ACTIVE_KEY, {
        "model": model, "base_url": base_url,
        "api_key": encrypt_secret(api_key), "dim": target_dim,
    })

    embedder = get_embedder(model, api_key, base_url)

    # 1) 重嵌所有 paragraphs（keyset 分批，避免大 offset）
    done = 0
    last_id = "00000000-0000-0000-0000-000000000000"
    while True:
        rows = (await session.execute(
            text("""
                SELECT id, content, knowledge_base_id FROM paragraphs
                WHERE is_active AND id > CAST(:last AS uuid)
                ORDER BY id LIMIT :lim
            """),
            {"last": last_id, "lim": _BATCH},
        )).fetchall()
        if not rows:
            break
        embs = await embedder.embed_batch([(r[1] or "") for r in rows])
        for (pid, _c, kb), e in zip(rows, embs):
            await upsert_embedding(session, pid, kb, e)
        await session.commit()
        done += len(rows)
        last_id = str(rows[-1][0])
        await _set_setting(session, PROGRESS_KEY, {
            "status": "running", "model": model, "target_dim": target_dim,
            "total": total, "done": done, "migrated": migrated, "started_at": started,
        })

    # 2) 重嵌 kb_entities（圖錨定向量需同維度）
    ent_rows = (await session.execute(text("SELECT id, name, aliases FROM kb_entities"))).fetchall()
    for i in range(0, len(ent_rows), _BATCH):
        batch = ent_rows[i:i + _BATCH]
        texts = []
        for _eid, name, aliases in batch:
            al = aliases if isinstance(aliases, list) else (json.loads(aliases) if aliases else [])
            texts.append(f"{name or ''} {' '.join(str(a) for a in al)}".strip())
        embs = await embedder.embed_batch(texts)
        for (eid, _n, _a), e in zip(batch, embs):
            await session.execute(
                text("UPDATE kb_entities SET embedding = CAST(:e AS vector), updated_at = now() WHERE id = :id"),
                {"e": str(e), "id": eid},
            )
        await session.commit()

    # 3) 維度有變 → 重建 ivfflat index
    if migrated:
        for stmt in (
            "CREATE INDEX IF NOT EXISTS idx_para_embed_vector ON paragraph_embeddings "
            "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)",
            "CREATE INDEX IF NOT EXISTS ix_kb_entities_vec ON kb_entities "
            "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)",
        ):
            await session.execute(text(stmt))
        await session.commit()

    # 4) 完成（active 已於重嵌前切換 → 此處只更新進度狀態）
    await _set_setting(session, PROGRESS_KEY, {
        "status": "done", "model": model, "target_dim": target_dim, "total": total,
        "done": done, "migrated": migrated, "entities": len(ent_rows),
        "started_at": started, "finished_at": datetime.datetime.utcnow().isoformat(),
    })
    log.info("reindex_done", model=model, dim=target_dim, paragraphs=done, entities=len(ent_rows), migrated=migrated)
    return {"status": "done", "total": total, "done": done, "dim": target_dim, "migrated": migrated}
