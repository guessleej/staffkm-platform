"""v5.13 Contextual Retrieval（Anthropic 法）— 進庫時為每塊補「全文脈絡」前綴再嵌。

原理：孤立的 chunk 常缺主詞/背景（"該條規定…" 不知指哪個法規）→ 向量召回失準。
做法：把「整份文件 + 本塊」丟給 LLM，產生一句把本塊定位於全文的脈絡，前綴到塊文字再嵌入。

成本：每塊 1 次 LLM 呼叫 → 很貴。故：
- 預設關（CONTEXTUAL_ENABLED）。
- 文件過大（CONTEXTUAL_MAX_DOC_CHARS）或塊太多（CONTEXTUAL_MAX_CHUNKS）→ 整份跳過（回原塊）。
- 併發上限 + 單塊逾時；任何失敗 → 該塊不加脈絡（回原塊），絕不阻斷入庫。
- 地端 LLM 無 prompt cache → doc 內容截斷到上限窗，避免每塊都送超長 prompt。
"""
from __future__ import annotations

import asyncio

import structlog
from openai import AsyncOpenAI

from app.config import settings

log = structlog.get_logger()

_SYS = (
    "你是文件脈絡標註器。給你整份文件與其中一個片段，請用「一句精簡的繁體中文」說明這個片段"
    "在全文中的脈絡（屬於哪個主題/章節/對象、承接什麼），好讓它被單獨檢索時也能被理解。"
    "只輸出那一句脈絡，不要重複片段原文、不要解釋、不要加引號。"
)


async def _one(client, model: str, doc_ctx: str, chunk: str, sem: asyncio.Semaphore) -> str:
    user = (
        f"<文件>\n{doc_ctx}\n</文件>\n\n"
        f"<片段>\n{chunk[:1500]}\n</片段>\n\n請給出這個片段的全文脈絡（一句）。"
    )
    try:
        async with sem:
            resp = await client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": _SYS},
                          {"role": "user", "content": user}],
                temperature=0,
                max_tokens=120,
                stream=False,
            )
        msg = resp.choices[0].message
        ctx = (msg.content or getattr(msg, "reasoning_content", "") or "").strip()
        return ctx.replace("\n", " ")[:300]
    except Exception as e:  # noqa: BLE001
        log.warning("contextualize_chunk_failed", error=str(e)[:160])
        return ""


async def contextualize_chunks(doc_text: str, chunks: list[str]) -> list[str]:
    """回傳與 chunks 等長的「脈絡前綴」清單（不適用/失敗處為空字串）。

    呼叫端負責把非空前綴接到塊文字前（"<脈絡>\\n<原塊>"）再嵌入。
    """
    n = len(chunks)
    if not settings.CONTEXTUAL_ENABLED or n == 0:
        return [""] * n
    if n > settings.CONTEXTUAL_MAX_CHUNKS or len(doc_text) > settings.CONTEXTUAL_MAX_DOC_CHARS:
        log.info("contextualize_skipped", chunks=n, doc_chars=len(doc_text),
                 reason="exceeds_limit")
        return [""] * n

    doc_ctx = doc_text[: settings.CONTEXTUAL_MAX_DOC_CHARS]
    client = AsyncOpenAI(
        api_key=settings.QUERY_EXPAND_API_KEY or "dummy",
        base_url=settings.QUERY_EXPAND_BASE_URL,
    )
    model = settings.CONTEXTUAL_MODEL or settings.QUERY_EXPAND_MODEL
    sem = asyncio.Semaphore(max(1, settings.CONTEXTUAL_CONCURRENCY))
    results = await asyncio.gather(
        *[_one(client, model, doc_ctx, c, sem) for c in chunks],
        return_exceptions=True,
    )
    out: list[str] = []
    for r in results:
        out.append(r if isinstance(r, str) else "")
    got = sum(1 for x in out if x)
    log.info("contextualized", chunks=n, with_context=got)
    return out
