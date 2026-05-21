"""Application Builder 代理人 — DB 驅動的可設定 AI 代理人

v2.8 對齊 MaxKB v2 智能體：function-calling agent loop。
  - simple mode（預設 / 向後相容）：單輪 RAG（retrieve_context → prompt → stream）
  - function_calling mode：暴露 search_knowledge_base + 綁定的 tool / workflow-tool
    給 LLM，由 LLM 自主決定 ReAct loop（tool_choice="auto"，最多
    AGENT_MAX_ITERATIONS 輪），最終答案 stream 出來。
  綁了任何 tool 的 application 自動升級成 function_calling（可由 config.agent_mode 覆寫）。

對外串流介面：
  - stream_events(ctx)：yield 結構化事件 {"type": "token"|"tool_call", ...}
    （chat_stream.py 用這個發 token / tool_call SSE）
  - stream_response(ctx)：只 yield token 字串（向後相容；內部包 stream_events）
"""
import json
from typing import AsyncIterator, Any

import httpx
import structlog
from openai import AsyncOpenAI

from app.config import settings
from app.core.base_agent import AgentContext
from app.core.providers import BaseProvider, ChatRequest, get_adapter
from app.core.secrets import decrypt_secret

log = structlog.get_logger()

# 內建 function：檢索綁定的知識庫
_SEARCH_KB_FUNCTION = "search_knowledge_base"


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
        # v5.9.28: 改用 LLM_* 系統 LLM (RFC-005) — 之前只讀 OPENAI_API_KEY 沒 base_url
        # → application 沒設 llm_model_id 時打 api.openai.com 空 key → Connection error
        self._api_key: str = settings.LLM_API_KEY or settings.OPENAI_API_KEY or "dummy"
        self._model: str = settings.LLM_MODEL or settings.OPENAI_MODEL
        self._base_url: str | None = settings.LLM_BASE_URL or None

        # 若有指定 llm_model_id，稍後透過 _init_llm_from_db 非同步載入
        self._llm_model_id: str | None = str(application["llm_model_id"]) if application.get("llm_model_id") else None

        # 建立預設 LLM 客戶端（可能在 _init_llm_from_db 後被替換）
        _client_kwargs: dict = {"api_key": self._api_key}
        if self._base_url:
            _client_kwargs["base_url"] = self._base_url
        self._llm = AsyncOpenAI(**_client_kwargs)

        # M3 中段-A：BaseProvider adapter（若 _init_llm_from_db 載入成功會被設定）
        self._provider: BaseProvider | None = None
        self._provider_type: str = "openai_compat"

        # Reranker 設定（可能在 _init_reranker_from_db / _resolve_default_reranker 後載入）
        self._reranker_config: dict | None = None
        self._reranker_model_id: str | None = str(self.config["reranker_model_id"]) if self.config.get("reranker_model_id") else None

        # ── Function-calling（v2.8 MaxKB 智能體）─────────────────────
        # 綁定的 tool（由 _init_tools_from_db 載入）；每個 dict 含
        # {id, name, description, kind, tool_type, config, input_schema, application_id}
        self._tools: list[dict[str, Any]] = []
        # workspace_id 在 stream 時由 ctx 帶入，用於 workflow sub-application 調用 audit
        self._workspace_id: str | None = None
        # agent 模式：config.agent_mode 可顯式指定；否則 create() 依是否綁 tool 自動決定
        self._agent_mode: str = str(self.config.get("agent_mode") or "").strip().lower()
        self._max_iterations: int = int(self.config.get("max_iterations", settings.AGENT_MAX_ITERATIONS))

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
        # v2.8：載入綁定的 tools（function-calling）
        if session is not None:
            await agent._init_tools_from_db(session)
        # 任務 2：app 沒設 reranker_model_id 時，看 system_settings 預設（cross_encoder 地端）
        if agent._reranker_config is None and session is not None:
            await agent._resolve_default_reranker(session)
        # 決定 agent 模式：未顯式指定 → 綁了 tool 就升 function_calling，否則 simple
        if agent._agent_mode not in ("simple", "function_calling"):
            agent._agent_mode = "function_calling" if agent._tools else "simple"
        return agent

    async def _init_tools_from_db(self, session) -> None:
        """載入 application 綁定的 tools。

        application.config.tool_ids（list[uuid str]）指定要暴露給 LLM 的 tool；
        每個 tool 轉成 OpenAI function schema 給 chat.completions(tools=[...])。
        只取同 workspace、is_enabled 的列（workspace 由 agent service require_member 保證）。
        """
        from sqlalchemy import text

        tool_ids = self.config.get("tool_ids", [])
        if isinstance(tool_ids, str):
            try:
                tool_ids = json.loads(tool_ids)
            except Exception:
                tool_ids = []
        if not tool_ids:
            return
        try:
            rows = await session.execute(
                text(
                    "SELECT id, name, description, kind, tool_type, config, "
                    "       input_schema, application_id "
                    "FROM tools "
                    "WHERE id::text = ANY(:ids) AND is_enabled = true"
                ),
                {"ids": [str(t) for t in tool_ids]},
            )
            for r in rows.fetchall():
                d = dict(r._mapping)
                cfg = d.get("config")
                if isinstance(cfg, str):
                    try:
                        cfg = json.loads(cfg)
                    except Exception:
                        cfg = {}
                schema = d.get("input_schema")
                if isinstance(schema, str):
                    try:
                        schema = json.loads(schema)
                    except Exception:
                        schema = {}
                self._tools.append(
                    {
                        "id": str(d["id"]),
                        "name": d.get("name") or f"tool_{str(d['id'])[:8]}",
                        "description": d.get("description") or "",
                        "kind": d.get("kind"),
                        "tool_type": d.get("tool_type") or d.get("kind"),
                        "config": cfg or {},
                        "input_schema": schema or {},
                        "application_id": str(d["application_id"]) if d.get("application_id") else None,
                    }
                )
            if self._tools:
                log.info(
                    "application_agent_tools_loaded",
                    app_id=self.app_id,
                    count=len(self._tools),
                    names=[t["name"] for t in self._tools],
                )
        except Exception as e:
            log.warning("application_agent_tools_load_failed", app_id=self.app_id, error=str(e))

    async def _resolve_default_reranker(self, session) -> None:
        """任務 2：app 未設 reranker_model_id 時，採用 system_settings 預設。

        若 reranker.default_type = 'cross_encoder' → 用地端 reranker container
        （RERANKER_ENDPOINT）。其他 type（cohere/http/ollama）需要明確 model 設定，
        這裡不自動帶（避免缺 api_key 而失敗），維持不 rerank。
        """
        from sqlalchemy import text

        try:
            row = await session.execute(
                text("SELECT value FROM system_settings WHERE key = 'reranker.default_type'")
            )
            r = row.fetchone()
            if not r:
                return
            val = r._mapping["value"]
            if isinstance(val, str):
                try:
                    val = json.loads(val)
                except Exception:
                    pass
            default_type = str(val).strip().strip('"').lower() if val is not None else ""
            if default_type == "cross_encoder":
                # 地端 cross_encoder：reranker container 走 sentence-transformers，
                # 無外部 API。container 未起時 rerank() 會 graceful fallback 原始排序。
                self._reranker_config = {
                    "type": "cross_encoder",
                    "endpoint": settings.RERANKER_ENDPOINT,
                }
                log.info(
                    "application_agent_default_reranker",
                    app_id=self.app_id,
                    reranker_type="cross_encoder",
                    endpoint=settings.RERANKER_ENDPOINT,
                )
        except Exception as e:
            log.warning("application_agent_default_reranker_failed", app_id=self.app_id, error=str(e))

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

            # Round 8-3：透過 decrypt_secret 解 fernet:/plain:/legacy；
            # 未設金鑰時 fallback 到原始字串
            api_key = decrypt_secret(api_key_enc) or settings.OPENAI_API_KEY

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

            # Round 8-3：統一走 decrypt_secret（自動辨識 fernet:/plain:/legacy base64）
            api_key: str | None = decrypt_secret(api_key_enc)

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

            # 若有 reranker 設定（app 自訂 or system_settings 預設），加入重排參數
            # 任務 2：多路召回 — 先撈較多候選（retrieval_top_k）再 rerank 取 rerank_top_n
            if self._reranker_config:
                search_payload["reranker"] = self._reranker_config
                search_payload["rerank_top_n"] = self.config.get("rerank_top_n", self.config.get("top_k", 5))
                # 預設拉高到 20（search.py 上限 50）以提升召回，再交給 reranker 收斂
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

    # ── 共用：溫度 / system prompt ──────────────────────────────────────────

    def _effective_temperature(self) -> float:
        temperature = float(self.config.get("temperature", 0.1))
        # v5.9.28: 部分 model 限定 temperature=1 (Kimi K2.6 / o1 / o3 系列)
        if any(self._model.startswith(p) for p in ("kimi-k2", "o1-", "o3-")):
            temperature = 1.0
        return temperature

    def _composed_system_prompt(self) -> str:
        # D-2：把 skill prompts 接在 system_prompt 前面（用 marker 分段）
        if self._skill_prompts:
            return "\n\n".join(self._skill_prompts) + "\n\n" + self.system_prompt
        return self.system_prompt

    # ── 串流回應（結構化事件）────────────────────────────────────────────────

    async def stream_events(self, ctx: AgentContext) -> AsyncIterator[dict]:
        """串流結構化事件給呼叫端（chat_stream.py 轉成 SSE）。

        yield 的 dict：
          {"type": "token", "data": str}                          — 回答片段
          {"type": "tool_call", "name", "input", "output", "status"}  — 工具呼叫過程
        最終 citations 由呼叫端從 ctx.citations 取（保持原行為）。

        simple mode：單輪 RAG（向後相容）。
        function_calling mode：暴露 tools 給 LLM 跑 ReAct loop。
        """
        self._workspace_id = ctx.workspace_id

        # function_calling 需走 OpenAI-compat self._llm 路徑（Anthropic adapter
        # 的 tool-call 較複雜，TODO 走 fallback）。provider adapter 不支援時退 simple。
        use_fc = self._agent_mode == "function_calling" and self._provider is None
        if use_fc:
            async for ev in self._stream_function_calling(ctx):
                yield ev
            return

        async for ev in self._stream_simple(ctx):
            yield ev

    async def stream_response(self, ctx: AgentContext) -> AsyncIterator[str]:
        """向後相容：只 yield token 字串（scenario chat / 無 metering 路徑用）。

        內部走 stream_events，把 token 事件抽出來；tool_call 事件靜默
        （這條路徑的呼叫端不發 tool_call SSE）。
        """
        async for ev in self.stream_events(ctx):
            if ev.get("type") == "token" and ev.get("data"):
                yield ev["data"]

    # ── simple mode：單輪 RAG（原行為）──────────────────────────────────────

    async def _stream_simple(self, ctx: AgentContext) -> AsyncIterator[dict]:
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
        messages = [
            {"role": "system", "content": self._composed_system_prompt()},
            *ctx.messages[:-1],
            {"role": "user", "content": rag_user_message},
        ]

        temperature = self._effective_temperature()
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
                    yield {"type": "token", "data": token}
            return

        try:
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
                    yield {"type": "token", "data": delta}
        except Exception as e:
            # 鐵則 5：LLM 錯誤 catch + 友善訊息，不可把原始 exception 當 token 串流
            log.warning("application_agent_llm_stream_failed", app_id=self.app_id, error=str(e))
            yield {"type": "token", "data": "（很抱歉，回應時發生錯誤，請稍後再試。）"}

    # ── function_calling mode：ReAct tool loop ──────────────────────────────

    def _build_function_specs(self) -> list[dict]:
        """組 OpenAI tools=[...] 規格：search_knowledge_base + 每個綁定 tool。"""
        specs: list[dict] = []
        # 內建：檢索知識庫（有綁 KB 才暴露）
        if self.kb_ids:
            specs.append(
                {
                    "type": "function",
                    "function": {
                        "name": _SEARCH_KB_FUNCTION,
                        "description": "在綁定的知識庫中檢索與問題相關的段落，回傳引用內容。"
                        "回答需要查資料時呼叫。",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "檢索查詢字串（通常是使用者問題或其關鍵字）",
                                }
                            },
                            "required": ["query"],
                        },
                    },
                }
            )
        for t in self._tools:
            schema = t.get("input_schema") or {}
            # input_schema 預期是 JSON Schema object；缺則給空 object
            if not isinstance(schema, dict) or schema.get("type") != "object":
                schema = {"type": "object", "properties": {}}
            specs.append(
                {
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t.get("description") or f"工具 {t['name']}",
                        "parameters": schema,
                    },
                }
            )
        return specs

    async def _execute_function(self, name: str, args: dict, ctx: AgentContext) -> dict:
        """執行 LLM 觸發的 function，回傳 {output, error} 結構。"""
        # 內建：知識庫檢索
        if name == _SEARCH_KB_FUNCTION:
            query = str(args.get("query") or (ctx.messages[-1]["content"] if ctx.messages else ""))
            citations = await self.retrieve_context(
                query,
                ctx.kb_ids,
                workspace_id=ctx.workspace_id,
                user_id=ctx.user_id,
                roles=ctx.roles,
            )
            # 累積到 ctx.citations 供前端顯示來源
            ctx.citations = (ctx.citations or []) + citations
            return {
                "output": {
                    "citations": [
                        {"doc_name": c.get("doc_name"), "content": c.get("content")}
                        for c in citations
                    ],
                    "count": len(citations),
                }
            }

        # 綁定的 tool（依 name 找）
        tool = next((t for t in self._tools if t["name"] == name), None)
        if tool is None:
            return {"error": f"未知的工具：{name}"}

        tool_type = (tool.get("tool_type") or tool.get("kind") or "").lower()
        try:
            if tool_type == "workflow":
                return await self._invoke_workflow_tool(tool, args, ctx)
            if tool_type == "http":
                from app.api.tool_exec import _exec_http
                res = await _exec_http(tool.get("config") or {}, args)
                return {"output": res.output if res.output is not None else res.text, "error": res.error}
            if tool_type == "mcp":
                from app.api.tool_exec import _exec_mcp
                res = await _exec_mcp(tool.get("config") or {}, args)
                return {"output": res.output, "error": res.error}
            return {"error": f"工具類型 {tool_type} 暫不支援於對話 loop（shell/custom 沙箱另案）"}
        except Exception as e:
            log.warning("application_agent_tool_exec_failed", app_id=self.app_id, tool=name, error=str(e))
            return {"error": str(e)}

    async def _invoke_workflow_tool(self, tool: dict, args: dict, ctx: AgentContext) -> dict:
        """workflow-type tool：invoke sub-application。

        TODO(v2.9)：真正 invoke 需走 in-process executor（避免 self-HTTP 缺
        gateway 認證 → 401）。目前回明確 error，由 LLM 在後續輪次據此回覆使用者，
        不阻斷整個 loop。schema / 載入路徑已就緒，待 executor 接線。
        """
        sub_app_id = tool.get("application_id")
        if not sub_app_id:
            return {"error": "workflow tool 未設定 application_id"}
        return {
            "error": "workflow-type tool 子應用調用尚未實作（TODO v2.9：in-process invoke）",
        }

    async def _stream_function_calling(self, ctx: AgentContext) -> AsyncIterator[dict]:
        """ReAct loop：tools=auto → 執行 tool → 回灌 → 收尾 stream。"""
        specs = self._build_function_specs()
        # 沒有任何 function 可用 → 退回 simple（理論上 create() 已避免，但雙保險）
        if not specs:
            async for ev in self._stream_simple(ctx):
                yield ev
            return

        temperature = self._effective_temperature()
        max_tokens = int(self.config.get("max_tokens", 2048))

        messages: list[dict] = [
            {"role": "system", "content": self._composed_system_prompt()},
            *ctx.messages,
        ]

        try:
            for _iteration in range(self._max_iterations):
                resp = await self._llm.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    tools=specs,
                    tool_choice="auto",
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=False,
                )
                choice = resp.choices[0]
                msg = choice.message
                tool_calls = getattr(msg, "tool_calls", None)

                if not tool_calls:
                    # 沒有要呼叫 tool → 這就是最終答案。為了串流體驗，重發一次 stream=True
                    # 收尾（messages 已含完整 context；不再給 tools，避免又觸發 tool）。
                    async for ev in self._final_stream(messages, temperature, max_tokens, msg):
                        yield ev
                    return

                # 把 assistant 的 tool_calls 訊息塞回 history
                messages.append(
                    {
                        "role": "assistant",
                        "content": msg.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                            }
                            for tc in tool_calls
                        ],
                    }
                )

                for tc in tool_calls:
                    fn_name = tc.function.name
                    try:
                        fn_args = json.loads(tc.function.arguments or "{}")
                    except Exception:
                        fn_args = {}
                    result = await self._execute_function(fn_name, fn_args, ctx)
                    output = result.get("output")
                    error = result.get("error")
                    # 任務 3：發 tool_call 事件給前端
                    yield {
                        "type": "tool_call",
                        "name": fn_name,
                        "input": fn_args,
                        "output": output,
                        "error": error,
                        "status": "error" if error else "success",
                    }
                    # 回灌 tool 結果（role:tool）給下一輪 LLM
                    tool_payload = {"error": error} if error else {"result": output}
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": json.dumps(tool_payload, ensure_ascii=False)[:8000],
                        }
                    )

            # 超過 max_iterations 仍未收尾 → 強制最後一次 stream（不帶 tools）收口
            async for ev in self._final_stream(messages, temperature, max_tokens, None):
                yield ev
        except Exception as e:
            # 鐵則 5：catch + 友善訊息
            log.warning("application_agent_fc_loop_failed", app_id=self.app_id, error=str(e))
            yield {"type": "token", "data": "（很抱歉，處理工具呼叫時發生錯誤，請稍後再試。）"}

    async def _final_stream(self, messages: list[dict], temperature: float, max_tokens: int, last_msg) -> AsyncIterator[dict]:
        """最終答案 stream=True 串流出來。

        若 last_msg 已有 content（LLM 第一輪就直接回答、沒呼叫 tool），且沒有
        後續 tool context，直接把它當 token 吐出，省一次 LLM 呼叫。否則重發 stream。
        """
        # 第一輪即答（無 tool_call）且有內容 → 直接輸出，不重發
        if last_msg is not None and getattr(last_msg, "content", None) and not getattr(last_msg, "tool_calls", None):
            yield {"type": "token", "data": last_msg.content}
            return
        try:
            stream = await self._llm.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield {"type": "token", "data": delta}
        except Exception as e:
            log.warning("application_agent_final_stream_failed", app_id=self.app_id, error=str(e))
            yield {"type": "token", "data": "（很抱歉，回應時發生錯誤，請稍後再試。）"}
