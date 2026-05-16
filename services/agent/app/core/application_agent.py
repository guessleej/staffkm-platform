"""Application Builder 代理人 — DB 驅動的可設定 AI 代理人"""
import json
from typing import AsyncIterator, Any

import httpx
import structlog
from openai import AsyncOpenAI

from app.config import settings
from app.core.base_agent import AgentContext
from app.core.providers import BaseProvider, ChatRequest, get_adapter

log = structlog.get_logger()


class ApplicationAgent:
    """
    從資料庫 applications 資料表載入設定的 AI 代理人。

    支援：
    - 自訂 system_prompt
    - 關聯知識庫 (knowledge_base_ids)
    - 可設定的 LLM 模型（若 llm_model_id 已設定則從 DB 取得模型設定）
    - RAG 檢索 + SSE 串流回應（與 BaseAdminAgent 相同模式）
    """

    def __init__(self, application: dict[str, Any]):
        self.application = application
        self.app_id = str(application.get("id", ""))
        self.system_prompt = application.get("system_prompt") or "你是一個知識庫問答助手，請根據提供的資料回答使用者問題。"
        self.welcome_message = application.get("welcome_message", "")

        # 知識庫 IDs — 可能是 list 或 JSON 字串
        kb_ids = application.get("knowledge_base_ids", [])
        if isinstance(kb_ids, str):
            kb_ids = json.loads(kb_ids)
        self.kb_ids: list[str] = kb_ids or []

        # Skill IDs（D-2）— 啟動時還只是 id 列表；stream_response 前由 create() 載入文字
        skill_ids = application.get("skill_ids", [])
        if isinstance(skill_ids, str):
            skill_ids = json.loads(skill_ids)
        self.skill_ids: list[str] = skill_ids or []
        self._skill_prompts: list[str] = []  # 載入後填入

        # 應用程式層級的 config（溫度、max_tokens 等）
        config = application.get("config", {})
        if isinstance(config, str):
            config = json.loads(config)
        self.config: dict[str, Any] = config or {}

        # LLM 設定（預設使用全域 settings）
        self._api_key: str = settings.OPENAI_API_KEY
        self._model: str = settings.OPENAI_MODEL
        self._base_url: str | None = None

        # 若有指定 llm_model_id，稍後透過 _init_llm_from_db 非同步載入
        self._llm_model_id: str | None = str(application["llm_model_id"]) if application.get("llm_model_id") else None

        # 建立預設 LLM 客戶端（可能在 _init_llm_from_db 後被替換）
        self._llm = AsyncOpenAI(api_key=self._api_key)

        # M3 中段-A：BaseProvider adapter（若 _init_llm_from_db 載入成功會被設定）
        self._provider: BaseProvider | None = None
        self._provider_type: str = "openai_compat"

        # Reranker 設定（可能在 _init_reranker_from_db 後載入）
        self._reranker_config: dict | None = None
        self._reranker_model_id: str | None = str(self.config["reranker_model_id"]) if self.config.get("reranker_model_id") else None

    # ── 工廠方法（非同步初始化）────────────────────────────────────────────

    @classmethod
    async def create(
        cls,
        application: dict[str, Any],
        session=None,
    ) -> "ApplicationAgent":
        """
        非同步工廠方法：建立 ApplicationAgent 並在必要時從 DB 載入 LLM 模型設定。

        Parameters
        ----------
        application : dict
            從資料庫取得的 application 記錄（dict 格式）。
        session : AsyncSession, optional
            SQLAlchemy 非同步 Session，用於查詢 ai_models / model_providers。
            若為 None，則使用全域 OpenAI 設定。
        """
        agent = cls(application)
        if agent._llm_model_id and session is not None:
            await agent._init_llm_from_db(session)
        if agent._reranker_model_id and session is not None:
            await agent._init_reranker_from_db(session)
        if agent.skill_ids and session is not None:
            await agent._init_skills_from_db(session)
        return agent

    async def _init_skills_from_db(self, session) -> None:
        """D-2：載入引用的 Skills，把每個 skill 的 prompt_template 收進
        self._skill_prompts，stream_response 前 prepend 到 system_prompt。
        Skill 必須屬於同 workspace（agent service 的 require_member 保證）。"""
        from sqlalchemy import text
        try:
            rows = await session.execute(
                text(
                    "SELECT id, name, prompt_template FROM skills "
                    "WHERE id::text = ANY(:ids)"
                ),
                {"ids": [str(s) for s in self.skill_ids]},
            )
            self._skill_prompts = []
            for r in rows.fetchall():
                d = dict(r._mapping)
                tpl = (d.get("prompt_template") or "").strip()
                if tpl:
                    # 加 marker 包住，方便日後 strip/debug
                    self._skill_prompts.append(
                        f"# Skill: {d.get('name', '')}\n{tpl}"
                    )
        except Exception as e:
            log.warning("application_agent_skill_load_failed", app_id=self.app_id, error=str(e))

    async def _init_llm_from_db(self, session) -> None:
        """從 DB 的 ai_models + model_providers 資料表載入 LLM 設定。"""
        from sqlalchemy import text

        try:
            row = await session.execute(
                text(
                    """
                    SELECT
                        m.model_name,
                        m.config AS model_config,
                        p.provider_type,
                        p.base_url,
                        p.api_key_enc,
                        p.config AS provider_config
                    FROM ai_models m
                    JOIN model_providers p ON p.id = m.provider_id
                    WHERE m.id = :model_id AND m.status = 'active'
                    """
                ),
                {"model_id": self._llm_model_id},
            )
            model_row = row.fetchone()
            if not model_row:
                log.warning(
                    "application_agent_model_not_found",
                    app_id=self.app_id,
                    model_id=self._llm_model_id,
                )
                return

            mapping = dict(model_row._mapping)
            self._model = mapping["model_name"]

            # 解析 provider 設定
            provider_type: str = mapping.get("provider_type", "openai")
            base_url: str | None = mapping.get("base_url")
            api_key_enc: str | None = mapping.get("api_key_enc")

            # api_key_enc 目前儲存為明文或加密文字，此處直接使用
            # 若有加密機制，在此處解密
            api_key = api_key_enc or settings.OPENAI_API_KEY

            # 從 model_config / provider_config 取得額外參數
            model_config = mapping.get("model_config") or {}
            if isinstance(model_config, str):
                model_config = json.loads(model_config)

            # 更新 LLM 客戶端
            client_kwargs: dict[str, Any] = {"api_key": api_key}
            if base_url:
                client_kwargs["base_url"] = base_url

            self._api_key = api_key
            self._base_url = base_url
            self._llm = AsyncOpenAI(**client_kwargs)

            # M3 中段-A：依 provider_type 選 adapter（Anthropic 等走專屬實作；
            # 其餘 fallback 到 OpenAI-compatible）
            try:
                adapter_cls = get_adapter(provider_type)
                provider_config = mapping.get("provider_config") or {}
                if isinstance(provider_config, str):
                    provider_config = json.loads(provider_config)
                self._provider = adapter_cls(
                    api_key=api_key,
                    base_url=base_url,
                    config=provider_config,
                )
                self._provider_type = provider_type
            except Exception as e:
                log.warning(
                    "application_agent_provider_init_failed",
                    app_id=self.app_id,
                    provider=provider_type,
                    error=str(e),
                )

            log.info(
                "application_agent_llm_loaded",
                app_id=self.app_id,
                model=self._model,
                provider=provider_type,
                adapter=type(self._provider).__name__ if self._provider else "openai-compat-fallback",
            )

        except Exception as e:
            log.warning(
                "application_agent_llm_init_failed",
                app_id=self.app_id,
                error=str(e),
            )
            # 降級：使用全域設定，不拋出例外

    async def _init_reranker_from_db(self, session) -> None:
        """從 DB 的 ai_models + model_providers 資料表載入 Reranker 設定。"""
        from sqlalchemy import text

        try:
            row = await session.execute(
                text(
                    """
                    SELECT
                        m.model_name,
                        m.config AS model_config,
                        p.provider_type,
                        p.base_url,
                        p.api_key_enc
                    FROM ai_models m
                    JOIN model_providers p ON p.id = m.provider_id
                    WHERE m.id = :model_id AND m.status = 'active' AND m.model_type = 'reranker'
                    """
                ),
                {"model_id": self._reranker_model_id},
            )
            model_row = row.fetchone()
            if not model_row:
                log.warning(
                    "application_agent_reranker_not_found",
                    app_id=self.app_id,
                    model_id=self._reranker_model_id,
                )
                return

            mapping = dict(model_row._mapping)
            model_name: str = mapping["model_name"]
            provider_type: str = mapping.get("provider_type", "custom")
            base_url: str | None = mapping.get("base_url")
            api_key_enc: str | None = mapping.get("api_key_enc")

            import base64
            api_key: str | None = None
            if api_key_enc:
                try:
                    api_key = base64.b64decode(api_key_enc.encode()).decode()
                except Exception:
                    api_key = api_key_enc  # 若解碼失敗則直接使用原值

            # 判斷 reranker 類型
            reranker_type = "cohere" if provider_type == "cohere" or (base_url and "cohere" in base_url) else "http"

            self._reranker_config = {
                "type": reranker_type,
                "model_name": model_name,
                "base_url": base_url,
                "api_key": api_key,
            }

            log.info(
                "application_agent_reranker_loaded",
                app_id=self.app_id,
                model=model_name,
                reranker_type=reranker_type,
            )

        except Exception as e:
            log.warning(
                "application_agent_reranker_init_failed",
                app_id=self.app_id,
                error=str(e),
            )
            # 降級：不使用 reranker

    # ── RAG 檢索 ────────────────────────────────────────────────────────────

    async def retrieve_context(
        self,
        query: str,
        extra_kb_ids: list[str] | None = None,
        workspace_id: str | None = None,
        user_id: str | None = None,
        roles: list[str] | None = None,
    ) -> list[dict]:
        """
        呼叫 Knowledge Service 取得相關段落（workspace-scoped）。

        合併 application.knowledge_base_ids 與呼叫端傳入的 extra_kb_ids。
        若 workspace_id 為 None，靠 knowledge service LegacyURLBridge 重寫到 default workspace。
        """
        merged_kb_ids = list(dict.fromkeys(self.kb_ids + (extra_kb_ids or [])))
        if not merged_kb_ids:
            return []

        try:
            search_payload: dict = {
                "query": query,
                "kb_ids": merged_kb_ids,
                "top_k": self.config.get("top_k", 5),
                "similarity_threshold": self.config.get("similarity_threshold", 0.45),
            }

            # 若有 reranker 設定，加入重排參數
            if self._reranker_config:
                search_payload["reranker"] = self._reranker_config
                search_payload["rerank_top_n"] = self.config.get("rerank_top_n", 5)
                search_payload["retrieval_top_k"] = self.config.get("retrieval_top_k", 20)

            # 組 URL：workspace-scoped 或 legacy
            if workspace_id:
                url = (
                    f"{settings.KNOWLEDGE_SERVICE_URL}"
                    f"/api/v1/workspace/{workspace_id}/knowledge/search"
                )
            else:
                url = f"{settings.KNOWLEDGE_SERVICE_URL}/api/v1/knowledge/search"
            headers: dict[str, str] = {}
            if user_id:
                headers["X-User-ID"] = user_id
            if roles:
                headers["X-User-Roles"] = ",".join(roles)

            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json=search_payload, headers=headers)
                if resp.status_code == 200:
                    return resp.json().get("data", {}).get("citations", [])
                log.warning(
                    "application_agent_retrieval_non_200",
                    app_id=self.app_id, status=resp.status_code, body=resp.text[:200],
                )
        except Exception as e:
            log.warning(
                "application_agent_retrieval_failed",
                app_id=self.app_id,
                error=str(e),
            )
        return []

    # ── RAG Prompt 建構 ──────────────────────────────────────────────────────

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

    # ── 串流回應 ─────────────────────────────────────────────────────────────

    async def stream_response(self, ctx: AgentContext) -> AsyncIterator[str]:
        """RAG 檢索 + LLM 串流回應，與 BaseAdminAgent 相同模式。"""
        user_query = ctx.messages[-1]["content"] if ctx.messages else ""

        # RAG 檢索（合併 ctx.kb_ids；帶 workspace + 認證 header 給下游 knowledge service）
        citations = await self.retrieve_context(
            user_query,
            ctx.kb_ids,
            workspace_id=ctx.workspace_id,
            user_id=ctx.user_id,
            roles=ctx.roles,
        )
        ctx.citations = citations

        rag_user_message = self._build_rag_prompt(citations, user_query)

        # D-2：把 skill prompts 接在 system_prompt 前面（用 marker 分段）
        composed_system = self.system_prompt
        if self._skill_prompts:
            composed_system = "\n\n".join(self._skill_prompts) + "\n\n" + self.system_prompt
        messages = [
            {"role": "system", "content": composed_system},
            *ctx.messages[:-1],
            {"role": "user", "content": rag_user_message},
        ]

        temperature = float(self.config.get("temperature", 0.1))
        max_tokens = int(self.config.get("max_tokens", 2048))

        # M3 中段-A：優先使用 BaseProvider adapter（支援 Anthropic / Gemini / …）；
        # 若未載入則 fallback 到既有 AsyncOpenAI 路徑（保持向後相容）。
        if self._provider is not None:
            req = ChatRequest(
                model=self._model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            async for token in self._provider.chat_stream(req):
                if token:
                    yield token
            return

        stream = await self._llm.chat.completions.create(
            model=self._model,
            messages=messages,
            stream=True,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
