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
    """單次對話的執行上下文（RFC-001 Stage 2: workspace-scoped）。"""

    def __init__(
        self,
        session_id: str,
        user_id: str,
        messages: list[dict],
        kb_ids: list[str],
        workspace_id: str | None = None,
        roles: list[str] | None = None,
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.messages = messages
        self.kb_ids = kb_ids
        # 多租戶：呼叫 knowledge / model service 等下游時帶在 header 中
        self.workspace_id = workspace_id
        self.roles = roles or []
        self.citations: list[dict] = []
        self.metadata: dict[str, Any] = {}


class BaseAdminAgent(ABC):
    """行政 AI 代理人基底類別，提供 RAG + 串流回應能力。"""

    scenario_id: str = ""
    scenario_name: str = ""
    scenario_description: str = ""

    SYSTEM_PROMPT: str = ""

    def __init__(self):
        # v5.9.11: 之前只讀 OPENAI_API_KEY 沒帶 base_url → 永遠打 api.openai.com 失敗
        # 改用 LLM_* 環境變數，跟 workflow executor 一致 (RFC-005 系統 LLM)
        client_kwargs: dict = {
            "api_key": settings.LLM_API_KEY or settings.OPENAI_API_KEY or "dummy",
        }
        if settings.LLM_BASE_URL:
            client_kwargs["base_url"] = settings.LLM_BASE_URL
        self._llm = AsyncOpenAI(**client_kwargs)

    async def retrieve_context(
        self,
        query: str,
        kb_ids: list[str],
        workspace_id: str | None = None,
        user_id: str | None = None,
        roles: list[str] | None = None,
    ) -> list[dict]:
        """呼叫 Knowledge Service 取得相關段落（workspace-scoped）。

        若未提供 workspace_id 則打 legacy 路徑，靠 knowledge service 的
        LegacyURLBridge 重寫到 default workspace（過渡期相容）。
        """
        try:
            if workspace_id:
                url = (
                    f"{settings.KNOWLEDGE_SERVICE_URL}"
                    f"/api/v1/workspace/{workspace_id}/knowledge/search"
                )
            else:
                url = f"{settings.KNOWLEDGE_SERVICE_URL}/api/v1/knowledge/search"
            headers = {}
            if user_id:
                headers["X-User-ID"] = user_id
            if roles:
                headers["X-User-Roles"] = ",".join(roles)
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    url,
                    json={
                        "query": query,
                        "kb_ids": kb_ids,
                        "top_k": 5,
                        "similarity_threshold": 0.45,
                    },
                    headers=headers,
                )
                if resp.status_code == 200:
                    return resp.json().get("data", {}).get("citations", [])
                log.warning(
                    "knowledge_retrieval_non_200",
                    status=resp.status_code, body=resp.text[:200],
                )
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

        # RAG 檢索（帶 workspace + user 認證 header 給下游 knowledge service）
        citations = await self.retrieve_context(
            user_query,
            ctx.kb_ids,
            workspace_id=ctx.workspace_id,
            user_id=ctx.user_id,
            roles=ctx.roles,
        )
        ctx.citations = citations

        rag_user_message = self._build_rag_prompt(citations, user_query)

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            *ctx.messages[:-1],
            {"role": "user", "content": rag_user_message},
        ]

        # v5.9.11: 部分 model 限定 temperature=1 (例如 Kimi K2.6 / o1 系列)
        model_name = settings.LLM_MODEL or settings.OPENAI_MODEL
        fixed_temp_models = ("kimi-k2", "o1-", "o3-")
        if any(model_name.startswith(p) for p in fixed_temp_models):
            temp = 1.0
        else:
            temp = settings.LLM_TEMPERATURE if settings.LLM_TEMPERATURE else 0.7

        stream = await self._llm.chat.completions.create(
            model=model_name,
            messages=messages,
            stream=True,
            temperature=temp,
            max_tokens=settings.LLM_MAX_TOKENS or 2048,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    @abstractmethod
    def get_suggested_questions(self) -> list[str]:
        """回傳此代理人的建議問題清單。"""
