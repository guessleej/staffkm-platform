"""v5.13 LLM Wiki — 用 LLM 把知識庫文件整理成可瀏覽的百科頁面（背景 Celery 任務）。

流程：每份文件 → 讀其段落 → LLM 整理成一頁 markdown wiki（標題/總覽/章節/關鍵事實，忠於原文）。
最後生成一頁「總覽/首頁」串起所有主題。進度寫 system_settings 'wiki.{kb_id}'，前端輪詢。
LLM 端點預設用地端 TAIDE（QUERY_EXPAND_* 同一顆）；任何單篇失敗只記 log、不中斷整體。
"""
from __future__ import annotations

import asyncio
import datetime
import json

import structlog
from openai import AsyncOpenAI
from sqlalchemy import text

from app.config import settings
from app.tasks.celery_app import celery_app
from staffkm_core.utils import database as _db

log = structlog.get_logger()

PROGRESS_KEY = "wiki"   # 實際 key = f"wiki.{kb_id}"


def _client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.WIKI_API_KEY or settings.QUERY_EXPAND_API_KEY or "dummy",
        base_url=settings.WIKI_BASE_URL or settings.QUERY_EXPAND_BASE_URL,
    )


def _model() -> str:
    return settings.WIKI_MODEL or settings.QUERY_EXPAND_MODEL


async def _llm(client: AsyncOpenAI, system: str, user: str, max_tokens: int = 1500) -> str:
    resp = await client.chat.completions.create(
        model=_model(),
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.3,
        max_tokens=max_tokens,
        stream=False,
    )
    msg = resp.choices[0].message
    return (msg.content or getattr(msg, "reasoning_content", "") or "").strip()


async def _set_status(s, kb_id: str, value: dict) -> None:
    await s.execute(
        text("""
            INSERT INTO system_settings (key, value, updated_at)
            VALUES (:k, CAST(:v AS jsonb), now())
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()
        """),
        {"k": f"{PROGRESS_KEY}.{kb_id}", "v": json.dumps(value, ensure_ascii=False)},
    )
    await s.commit()


_PAGE_SYS = (
    "你是知識整理員。把使用者給的單篇文件內容，整理成一頁百科式 wiki 頁面，用繁體中文 Markdown 輸出：\n"
    "- 開頭一段「總覽」說明這份文件在講什麼\n"
    "- 數個 `## 小標題` 章節，把重點分門別類\n"
    "- 適時用條列與 **粗體** 標出關鍵事實/數字/期限\n"
    "忠於原文、不杜撰、不加入原文沒有的資訊。只輸出 Markdown 內文，不要前後多餘說明。"
)

_INDEX_SYS = (
    "你是知識庫編輯。根據使用者給的「各主題標題與摘要」，寫這個知識庫的首頁總覽，用繁體中文 Markdown：\n"
    "- 一段話介紹這個知識庫涵蓋什麼、適合誰查\n"
    "- 一個 `## 主題目錄` 條列各主題（用主題標題，可加一句話說明）\n"
    "只輸出 Markdown，不要多餘說明。"
)


async def _async_generate(kb_id: str) -> dict:
    started = datetime.datetime.utcnow().isoformat()
    async with _db._session_factory() as s:
        # 取 KB 名稱 + workspace
        kb_row = (await s.execute(
            text("SELECT name, workspace_id FROM knowledge_bases WHERE id = CAST(:k AS uuid)"),
            {"k": kb_id},
        )).first()
        kb_name = kb_row[0] if kb_row else "知識庫"
        ws = str(kb_row[1]) if kb_row and kb_row[1] else None

        docs = (await s.execute(
            text("""SELECT id, name FROM documents
                    WHERE knowledge_base_id = CAST(:k AS uuid) AND status = 'ready'
                    ORDER BY created_at LIMIT :lim"""),
            {"k": kb_id, "lim": settings.WIKI_MAX_DOCS},
        )).fetchall()
        total = len(docs)
        await _set_status(s, kb_id, {"status": "running", "total": total, "done": 0,
                                     "started_at": started})

        if total == 0:
            await _set_status(s, kb_id, {"status": "error", "error": "知識庫沒有可用文件",
                                         "total": 0, "done": 0, "started_at": started})
            return {"status": "error", "reason": "no documents"}

        # 清舊 wiki
        await s.execute(text("DELETE FROM kb_wiki_pages WHERE knowledge_base_id = CAST(:k AS uuid)"),
                        {"k": kb_id})
        await s.commit()

        client = _client()
        summaries: list[str] = []
        done = 0
        for oi, (doc_id, doc_name) in enumerate(docs, start=1):
            try:
                paras = (await s.execute(
                    text("""SELECT content FROM paragraphs
                            WHERE document_id = :d AND is_active = true
                            ORDER BY order_index"""),
                    {"d": str(doc_id)},
                )).fetchall()
                body = "\n".join((p[0] or "") for p in paras)[: settings.WIKI_DOC_CHARS]
                if not body.strip():
                    continue
                md = await _llm(client, _PAGE_SYS, f"文件名：{doc_name}\n\n內容：\n{body}")
                if not md:
                    continue
                await s.execute(
                    text("""INSERT INTO kb_wiki_pages
                            (knowledge_base_id, document_id, workspace_id, title, content, order_index, is_index)
                            VALUES (CAST(:k AS uuid), :d, :ws, :t, :c, :oi, false)"""),
                    {"k": kb_id, "d": str(doc_id), "ws": ws,
                     "t": (doc_name or "未命名")[:256], "c": md, "oi": oi},
                )
                await s.commit()
                summaries.append(f"- {doc_name}：{md.splitlines()[0][:80] if md else ''}")
            except Exception as e:  # noqa: BLE001
                log.warning("wiki_page_failed", doc=str(doc_id), error=str(e)[:160])
            done += 1
            await _set_status(s, kb_id, {"status": "running", "total": total, "done": done,
                                         "started_at": started})

        # 首頁總覽
        try:
            idx_md = await _llm(
                client, _INDEX_SYS,
                f"知識庫名稱：{kb_name}\n\n各主題：\n" + "\n".join(summaries[:60]),
                max_tokens=1000,
            )
            if idx_md:
                await s.execute(
                    text("""INSERT INTO kb_wiki_pages
                            (knowledge_base_id, document_id, workspace_id, title, content, order_index, is_index)
                            VALUES (CAST(:k AS uuid), NULL, :ws, :t, :c, 0, true)"""),
                    {"k": kb_id, "ws": ws, "t": f"{kb_name} · 總覽"[:256], "c": idx_md},
                )
                await s.commit()
        except Exception as e:  # noqa: BLE001
            log.warning("wiki_index_failed", error=str(e)[:160])

        await _set_status(s, kb_id, {"status": "done", "total": total, "done": done,
                                     "started_at": started,
                                     "finished_at": datetime.datetime.utcnow().isoformat()})
        log.info("wiki_generated", kb_id=kb_id, pages=done)
        return {"status": "done", "pages": done}


@celery_app.task(name="app.tasks.wiki_gen.generate_wiki")
def generate_wiki(kb_id: str) -> dict:
    return asyncio.run(_async_generate(kb_id))
