"""所有行政場景代理人的抽象基底類別"""
import uuid
from abc import ABC, abstractmethod
from typing import AsyncIterator, Any

import httpx
import structlog
from openai import AsyncOpenAI

from app.config import settings

log = structlog.get_logger()


class AgentContext:
    """單次對話的執行上下文。"""

    def __init__(
        self,
        session_id: str,
        user_id: str,
        messages: list[dict],
        kb_ids: list[str],
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.messages = messages
        self.kb_ids = kb_ids
        self.citations: list[dict] = []
        self.metadata: dict[str, Any] = {}


class BaseAdminAgent(ABC):
    """行政 AI 代理人基底類別，提供 RAG + 串流回應能力。"""

    scenario_id: str = ""
    scenario_name: str = ""
    scenario_description: str = ""

    SYSTEM_PROMPT: str = ""

    def __init__(self):
        self._llm = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def retrieve_context(self, query: str, kb_ids: list[str]) -> list[dict]:
        """呼叫 Knowledge Service 取得相關段落。"""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{settings.KNOWLEDGE_SERVICE_URL}/api/v1/knowledge/search",
                    json={
                        "query": query,
                        "kb_ids": kb_ids,
                        "top_k": 5,
                        "similarity_threshold": 0.45,
                    },
                )
                if resp.status_code == 200:
                    return resp.json().get("data", {}).get("citations", [])
        except Exception as e:
            log.warning("knowledge_retrieval_failed", error=str(e))
        return []

    def _build_rag_prompt(self, context_docs: list[dict], query: str) -> str:
        if not context_docs:
            return query
        context_text = "\n\n".join(
            f"【來源：{d['doc_name']}】\n{d['content']}" for d in context_docs
        )
        return f"""以下是與問題相關的參考資料：

{context_text}

---
請根據上述參考資料回答以下問題（若資料中無明確答案，請說明並提供一般性建議）：

{query}"""

    async def stream_response(self, ctx: AgentContext) -> AsyncIterator[str]:
        user_query = ctx.messages[-1]["content"] if ctx.messages else ""

        # RAG 檢索
        citations = await self.retrieve_context(user_query, ctx.kb_ids)
        ctx.citations = citations

        rag_user_message = self._build_rag_prompt(citations, user_query)

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            *ctx.messages[:-1],
            {"role": "user", "content": rag_user_message},
        ]

        stream = await self._llm.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            stream=True,
            temperature=0.1,
            max_tokens=2048,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    @abstractmethod
    def get_suggested_questions(self) -> list[str]:
        """回傳此代理人的建議問題清單。"""
