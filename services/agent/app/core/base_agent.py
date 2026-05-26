"""所有行政場景代理人的抽象基底類別"""
import uuid
from abc import ABC, abstractmethod
from typing import AsyncIterator, Any

import httpx
import structlog
from openai import AsyncOpenAI

from app.config import settings

log = structlog.get_logger()


def split_trailing_newlines(s: str) -> tuple[str, str]:
    """切出 (可送出前段, 結尾連續換行)。

    SSE 規範會吃掉 data 值的「結尾 \\n」，且地端模型（gemma4 等）常把換行單獨
    當一個 token 串出（純 "\\n" / "\\n\\n"）→ 經 SSE 中繼會遺失，答案擠成一坨。
    解法：把結尾換行留到下一個有內容的 token 前面 → 換行變「內部換行」，SSE 不會吃。
    """
    i = len(s)
    while i > 0 and s[i - 1] == "\n":
        i -= 1
    return s[:i], s[i:]


def _normalize_openai_base(base: str | None, provider_type: str) -> str | None:
    """OpenAI 相容聊天端點需要 /v1；ollama 原生 base_url（給 verify 用）沒帶 → 補上。"""
    if not base:
        return base
    b = base.rstrip("/")
    if not b.endswith("/v1"):
        b = b + "/v1"
    return b


async def resolve_system_llm() -> tuple[str, str | None, str]:
    """解析「系統預設聊天模型」。

    優先讀 system_settings.default.llm（admin/models 頁選的模型名）→ 連回
    ai_models + model_providers 取得 base_url / api_key；查無設定或任何錯誤時
    fallback 用環境變數（LLM_MODEL / LLM_BASE_URL / LLM_API_KEY）。

    回傳 (model_name, base_url, api_key)。
    """
    env_model = settings.LLM_MODEL or settings.OPENAI_MODEL
    env_base = settings.LLM_BASE_URL or None
    env_key = settings.LLM_API_KEY or settings.OPENAI_API_KEY or "dummy"
    try:
        import json
        from sqlalchemy import text
        from staffkm_core.secrets import decrypt_secret
        from staffkm_core.utils import database as _db

        # get_session() 是 FastAPI 依賴用的 async generator，不能直接當 context
        # manager；這裡用底層 session factory（同 chat_stream.py 的做法）。
        sf = getattr(_db, "_read_session_factory", None) or getattr(_db, "_session_factory", None)
        if sf is None:
            return env_model, env_base, env_key
        async with sf() as session:
            row = (await session.execute(text(
                "SELECT value FROM system_settings WHERE key = 'default.llm'"
            ))).fetchone()
            if not row or row.value in (None, "", '""'):
                return env_model, env_base, env_key

            raw = row.value
            if isinstance(raw, str):
                try:
                    raw = json.loads(raw)
                except Exception:  # noqa: BLE001
                    pass
            model_name = raw if isinstance(raw, str) else (
                raw.get("model_name") if isinstance(raw, dict) else None
            )
            if not model_name:
                return env_model, env_base, env_key

            prov = (await session.execute(text("""
                SELECT p.provider_type, p.base_url, p.api_key_enc
                FROM ai_models m JOIN model_providers p ON p.id = m.provider_id
                WHERE m.model_name = :mn AND m.model_type = 'llm' AND m.status = 'active'
                ORDER BY m.is_default DESC
                LIMIT 1
            """), {"mn": model_name})).fetchone()
            if not prov:
                # 設了模型名但找不到 provider → 至少用該模型名 + env 連線設定
                return model_name, env_base, env_key

            base = _normalize_openai_base(prov.base_url or env_base, prov.provider_type)
            # ollama / 地端通常不需 key；有 key（如 Moonshot）才解（統一走 decrypt_secret：
            # fernet:/plain:/legacy-base64 皆可，不再 raw base64）
            key = "dummy"
            if prov.api_key_enc:
                key = decrypt_secret(prov.api_key_enc) or env_key
            return model_name, base, key
    except Exception as e:  # noqa: BLE001 — DB 不可達不致命，fallback env
        log.warning("resolve_system_llm_failed", error=str(e))
        return env_model, env_base, env_key


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

        # 解析系統預設模型（admin/models 頁選的 default.llm）→ 沒設才 fallback env。
        # 每次請求重解，所以在 UI 改了預設、按儲存後即時生效，不必重啟 agent。
        model_name, base_url, api_key = await resolve_system_llm()
        client_kwargs: dict = {"api_key": api_key or "dummy"}
        if base_url:
            client_kwargs["base_url"] = base_url
        llm = AsyncOpenAI(**client_kwargs)

        # v5.9.11: 部分 model 限定 temperature=1 (例如 Kimi K2.6 / o1 系列)
        fixed_temp_models = ("kimi-k2", "o1-", "o3-")
        if any(model_name.startswith(p) for p in fixed_temp_models):
            temp = 1.0
        else:
            temp = settings.LLM_TEMPERATURE if settings.LLM_TEMPERATURE else 0.7

        # v5.9.12: API 錯誤改成中文友善訊息，不要直接把原始 JSON 當 assistant
        # 回應串給 user（之前 401 會看到 "Error code: 401 - {...}"）
        try:
            stream = await llm.chat.completions.create(
                model=model_name,
                messages=messages,
                stream=True,
                temperature=temp,
                max_tokens=settings.LLM_MAX_TOKENS or 2048,
            )
            pending = ""  # 暫存結尾換行，避免 SSE 吃掉純換行 token（見 split_trailing_newlines）
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if not delta:
                    continue
                head, pending = split_trailing_newlines(pending + delta)
                if head:
                    yield head
        except Exception as e:
            msg = str(e)
            log.error("llm_call_failed", model=model_name, error=msg[:300])
            if "401" in msg or "Incorrect API key" in msg or "Invalid Authentication" in msg:
                yield "⚠️ LLM 認證失敗（API key 無效或已撤銷）。請至 /admin/models 重新設定有效的 API key 並重啟 agent。"
            elif "429" in msg or "rate" in msg.lower():
                yield "⚠️ LLM 用量超出（rate limit）。請稍後再試或檢查帳戶配額。"
            elif "Connection" in msg or "timeout" in msg.lower():
                yield "⚠️ 連線 LLM 服務失敗。請檢查 LLM_BASE_URL 設定與網路可達性。"
            else:
                yield f"⚠️ LLM 呼叫失敗：{msg[:200]}"

    @abstractmethod
    def get_suggested_questions(self) -> list[str]:
        """回傳此代理人的建議問題清單。"""
