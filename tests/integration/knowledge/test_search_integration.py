"""Hybrid 檢索整合測試（真 pgvector）。

守的是召回核心 `app.core.vectorstore`：向量 cosine 排序 / FTS（含 CJK 分字）/
hybrid RRF 合併 / 相似度閾值過濾 / KB 隔離 / `SET LOCAL ivfflat.probes`。

純邏輯單元（test_search_fusion）只測 RRF 融合的就地修改；這層補「真 SQL」：
pgvector `<=>` cosine、`websearch_to_tsquery('simple')` 對 CJK 分字的比對、
FULL OUTER JOIN 的 RRF merge、`CAST(:emb AS vector)` bind。維度用 vector(4) 手刻。
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.config import settings
from app.core.vectorstore import (
    hybrid_search,
    set_ivfflat_probes,
    tokenize_for_fts,
    update_search_vector,
    upsert_embedding,
)

pytestmark = pytest.mark.asyncio


async def _seed_doc(session, kb_id) -> uuid.UUID:
    did = uuid.uuid4()
    await session.execute(
        text("INSERT INTO documents (id, name) VALUES (CAST(:id AS uuid), :n)"),
        {"id": str(did), "n": "doc"},
    )
    return did


async def _seed_para(session, kb_id, doc_id, content, embedding) -> uuid.UUID:
    pid = uuid.uuid4()
    await session.execute(
        text("""
            INSERT INTO paragraphs (id, document_id, knowledge_base_id, content, is_active)
            VALUES (CAST(:id AS uuid), CAST(:doc AS uuid), CAST(:kb AS uuid), :c, true)
        """),
        {"id": str(pid), "doc": str(doc_id), "kb": str(kb_id), "c": content},
    )
    await update_search_vector(session, pid, content)
    await upsert_embedding(session, pid, kb_id, embedding)
    return pid


# 4 維手刻向量：A/B/C 互相正交，query 偏向某一軸即可預測 cosine 排序。
_A = [1.0, 0.0, 0.0, 0.0]
_B = [0.0, 1.0, 0.0, 0.0]
_C = [0.0, 0.0, 1.0, 0.0]


# ── 向量模式：cosine 排序 + 閾值 ─────────────────────────────────────────
async def test_vector_mode_ranks_by_cosine(db_session):
    kb = uuid.uuid4()
    doc = await _seed_doc(db_session, kb)
    pa = await _seed_para(db_session, kb, doc, "台灣請假政策規定", _A)
    await _seed_para(db_session, kb, doc, "差勤表單填寫", _B)
    await _seed_para(db_session, kb, doc, "報帳流程", _C)
    await db_session.commit()

    rows = await hybrid_search(db_session, kb, [0.9, 0.1, 0.0, 0.0], "x",
                               top_k=5, similarity_threshold=0.0, search_mode="vector")
    assert str(rows[0]["id"]) == str(pa)            # 最接近 A 軸
    assert rows[0]["score"] >= rows[-1]["score"]    # 由高到低


async def test_vector_threshold_filters_low_similarity(db_session):
    kb = uuid.uuid4()
    doc = await _seed_doc(db_session, kb)
    pa = await _seed_para(db_session, kb, doc, "台灣請假政策", _A)
    await _seed_para(db_session, kb, doc, "差勤表單", _B)
    await _seed_para(db_session, kb, doc, "報帳流程", _C)
    await db_session.commit()

    rows = await hybrid_search(db_session, kb, [0.9, 0.1, 0.0, 0.0], "x",
                               top_k=5, similarity_threshold=0.5, search_mode="vector")
    ids = [str(r["id"]) for r in rows]
    assert ids == [str(pa)]   # 只有 A 過 0.5（B≈0.11、C≈0）


# ── FTS 模式：CJK 分字比對 ────────────────────────────────────────────────
async def test_fts_mode_matches_cjk_content(db_session):
    kb = uuid.uuid4()
    doc = await _seed_doc(db_session, kb)
    pa = await _seed_para(db_session, kb, doc, "台灣請假政策規定", _A)
    await _seed_para(db_session, kb, doc, "差勤表單填寫", _B)
    await db_session.commit()

    rows = await hybrid_search(db_session, kb, _C, "請假", top_k=5, search_mode="fts")
    ids = [str(r["id"]) for r in rows]
    assert ids == [str(pa)]   # 只有含「請假」的段落命中


# ── Hybrid：向量 + FTS 兩路 RRF 合併 ─────────────────────────────────────
async def test_hybrid_merges_vector_and_fts(db_session):
    kb = uuid.uuid4()
    doc = await _seed_doc(db_session, kb)
    pa = await _seed_para(db_session, kb, doc, "台灣請假政策規定", _A)   # FTS 命中「請假」
    pb = await _seed_para(db_session, kb, doc, "差勤表單填寫", _B)        # 向量接近 query
    await _seed_para(db_session, kb, doc, "報帳流程", _C)
    await db_session.commit()

    # query 向量偏 B、query_text 命中 A → hybrid 應同時收 A（FTS）與 B（向量）
    rows = await hybrid_search(db_session, kb, [0.0, 0.9, 0.1, 0.0], "請假",
                               top_k=5, similarity_threshold=0.5, search_mode="hybrid")
    ids = {str(r["id"]) for r in rows}
    assert str(pa) in ids and str(pb) in ids


# ── KB 隔離：只回該 kb 的段落 ─────────────────────────────────────────────
async def test_kb_isolation(db_session):
    kb1, kb2 = uuid.uuid4(), uuid.uuid4()
    doc = await _seed_doc(db_session, kb1)
    p1 = await _seed_para(db_session, kb1, doc, "台灣請假政策", _A)
    await _seed_para(db_session, kb2, doc, "台灣請假政策", _A)  # 同內容、不同 KB
    await db_session.commit()

    rows = await hybrid_search(db_session, kb1, [1.0, 0.0, 0.0, 0.0], "請假",
                               top_k=5, similarity_threshold=0.0, search_mode="vector")
    ids = [str(r["id"]) for r in rows]
    assert ids == [str(p1)]   # kb2 的段落不得外洩


# ── ivfflat.probes：SET LOCAL 真生效（v5.11.4 召回根因修）────────────────
async def test_ivfflat_probes_set_local(db_session):
    await set_ivfflat_probes(db_session)
    val = (await db_session.execute(
        text("SELECT current_setting('ivfflat.probes')"))).scalar()
    assert val == str(settings.IVFFLAT_PROBES)   # 預設 10，非 pgvector 預設的 1


# ── CJK 分字（純函式，但召回正確性的前置；async 純為配合 module asyncio mark）──────
async def test_tokenize_for_fts_cjk_spacing():
    assert tokenize_for_fts("台灣請假") == "台 灣 請 假"
    assert tokenize_for_fts("policy 政策") == "policy 政 策"
