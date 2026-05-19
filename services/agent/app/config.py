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

    # ── 雲端 LLM（選用，預設空）────────────────────────────────
    OPENAI_API_KEY:    str = ""
    ANTHROPIC_API_KEY: str = ""
    GOOGLE_API_KEY:    str = ""
    # v5.2: Bailian (DashScope) — text-to-video / image-to-video
    DASHSCOPE_API_KEY: str = ""

    # ── Legacy（v1 相容，下一版移除）──────────────────────────
    OPENAI_MODEL: str = "gemma4:e4b"   # 舊欄位，導向地端

    MAX_CONTEXT_MESSAGES: int = 20

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
