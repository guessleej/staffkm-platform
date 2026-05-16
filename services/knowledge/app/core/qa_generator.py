"""Q&A 自動生成（Round 10-2）。

對單一 paragraph 文本呼叫 LLM，產出 N 組 question/answer。
回退鏈：
1. 設定有 OPENAI_API_KEY → 走 AsyncOpenAI
2. 否則拋 RuntimeError（前端 toast 顯示）

prompt 設計刻意保守、要求 strict JSON output，便於解析。
"""
from __future__ import annotations

import json
from typing import Any

import structlog

from app.config import settings

log = structlog.get_logger()


SYSTEM_PROMPT = (
    "你是企業內部知識庫的 Q&A 整理員。"
    "我會給你一段文字，請你產出 {n} 組『繁體中文』問題與答案，"
    "問題要像員工會真的問的口語，答案精煉、直接，不超過 3 句。"
    "嚴格用以下 JSON 格式輸出，不要加任何說明或 markdown：\n"
    "{{\"qa\":[{{\"question\":\"…\",\"answer\":\"…\"}}, ...]}}"
)


async def generate_qa_for_text(text: str, *, n: int = 3, model: str | None = None) -> list[dict[str, str]]:
    """產出 n 組 {question, answer}。失敗 raise RuntimeError。"""
    if not text or not text.strip():
        return []
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("未設定 OPENAI_API_KEY — 無法產生 Q&A（或先到 admin/models 設定供應商）")

    try:
        from openai import AsyncOpenAI
    except ImportError as e:
        raise RuntimeError("openai 套件未安裝") from e

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    chosen_model = model or getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")

    try:
        resp = await client.chat.completions.create(
            model=chosen_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT.format(n=n)},
                {"role": "user",   "content": text[:3000]},  # 防爆 token
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        raw = (resp.choices[0].message.content or "").strip()
    except Exception as e:
        log.warning("qa_llm_call_failed", error=str(e))
        raise RuntimeError(f"LLM 呼叫失敗：{e}") from e

    try:
        data = json.loads(raw)
        pairs = data.get("qa") or []
    except Exception:
        log.warning("qa_parse_failed", raw=raw[:200])
        raise RuntimeError("LLM 回傳 JSON 解析失敗")

    # 防呆：限制長度、剔除空白
    out: list[dict[str, str]] = []
    for p in pairs[: max(1, n)]:
        q = str(p.get("question", "")).strip()
        a = str(p.get("answer", "")).strip()
        if q and a:
            out.append({"question": q, "answer": a, "source": "auto"})
    return out
