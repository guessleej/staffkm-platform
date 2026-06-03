from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DB_URL: str = "postgresql+asyncpg://staffkm:staffkm_secret@postgres:5432/staffkm?ssl=disable"
    # v4.0 P6: optional read replica URL；空字串 = 用 DB_URL（單 pool 行為）
    DB_READ_URL: str = ""
    REDIS_URL: str = "redis://:staffkm_redis@redis:6379/2"
    KNOWLEDGE_SERVICE_URL: str = "http://knowledge:8001"

    # ── LLM：地端優先（RFC-005）────────────────────────────────
    # 預設用內網 Ollama 跑 gemma4:e4b，無需外部 API key 即可完整運行
    # 雲端 provider 仍可用，需 workspace 主動 opt-in
    LLM_PROVIDER:     str   = "ollama"               # ollama | openai | anthropic | google
    LLM_MODEL:        str   = "gemma4:e4b"
    LLM_BASE_URL:     str   = "http://embedder:11434/v1"
    LLM_API_KEY:      str   = "dummy"                # Ollama 不檢查
    LLM_TEMPERATURE:  float = 0.7
    LLM_MAX_TOKENS:   int   = 2048

    # v5.13: workflow 圖像理解節點 — 地端 vision 走 ollama 原生 /api/chat + think:False。
    #   思考型多模態模型（gemma4:e4b）經 OpenAI-compat 關不掉 thinking → 回空。雲端 vision 設 false。
    VISION_USE_OLLAMA_NATIVE: bool = True

    # v5.13: 客服機器人安全護欄（L2 輸入防護 + L3 RAG 接地拒答）。
    #   - WRAP_INPUT（預設開）：把使用者輸入結構化包裹進 data 區，防注入覆寫 system（安全、不影響正常答）。
    #   - STRICT_MODE（全域預設關）：嚴格客服模式 = RAG 無命中即罐頭拒答 + system prompt 硬化 + 偵測到
    #     注入即拒答。可由 application.config={"guardrail_strict":true} 單一應用開（不需改全域）。
    GUARDRAIL_WRAP_INPUT:  bool = True
    GUARDRAIL_STRICT_MODE: bool = False
    GUARDRAIL_NO_ANSWER_MESSAGE: str = (
        "很抱歉，我在目前的知識庫中找不到與您問題直接相關的資料。"
        "建議您換個關鍵字描述，或聯繫真人客服協助。"
    )
    GUARDRAIL_BLOCKED_MESSAGE: str = (
        "很抱歉，我只能協助與本服務知識庫相關的問題，無法執行此要求。"
    )

    # ── 雲端 LLM（選用，預設空）────────────────────────────────
    OPENAI_API_KEY:    str = ""
    ANTHROPIC_API_KEY: str = ""
    GOOGLE_API_KEY:    str = ""
    # v5.2: Bailian (DashScope) — text-to-video / image-to-video
    DASHSCOPE_API_KEY: str = ""

    # ── Legacy（v1 相容，下一版移除）──────────────────────────
    OPENAI_MODEL: str = "gemma4:e4b"   # 舊欄位，導向地端

    MAX_CONTEXT_MESSAGES: int = 20

    # ── Agent function-calling loop（MaxKB v2 智能體）──────────────
    # 綁了 tool 的 application 走 ReAct 式 function-calling；safety 上限避免無限迴圈
    AGENT_MAX_ITERATIONS: int = 5
    # cross_encoder 地端 reranker container endpoint（v3.4 P3 profile=reranker）
    RERANKER_ENDPOINT: str = "http://reranker:8000"

    # ── v3.4 P2: SMTP for quota alert email channel ─────────────
    # 沒設 SMTP_HOST 時 email dispatch 仍 log-only（dev 友善）
    SMTP_HOST:     str = ""
    SMTP_PORT:     int = 587
    SMTP_USER:     str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM:     str = "noreply@staffkm.local"
    SMTP_USE_TLS:  bool = True

    # ── v4.7+v4.8 G+H: Stripe billing ──────────────────────────
    # 不設 STRIPE_SECRET_KEY → billing 端點 503，其他功能不受影響
    STRIPE_SECRET_KEY:     str = ""  # sk_test_... or sk_live_...
    STRIPE_WEBHOOK_SECRET: str = ""  # whsec_...
    STRIPE_PRICE_STARTER:  str = ""  # price_xxx (monthly $29)
    STRIPE_PRICE_PRO:      str = ""  # price_xxx (monthly $199)
    STRIPE_PRICE_USAGE:    str = ""  # price_xxx (metered, $0.001/1k tokens 之類)
    BILLING_PUBLIC_URL:    str = "http://localhost"  # for success/cancel redirects


settings = Settings()
