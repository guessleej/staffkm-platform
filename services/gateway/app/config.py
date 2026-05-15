from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    VERSION: str = "1.0.0"
    ENV: str = "development"
    SECRET_KEY: str = "changeme"
    JWT_ALGORITHM: str = "HS256"

    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:80"]

    # 下游服務
    KNOWLEDGE_SERVICE_URL: str = "http://knowledge:8001"
    AGENT_SERVICE_URL: str = "http://agent:8002"
    AUTH_SERVICE_URL: str = "http://auth:8003"
    INTEGRATION_SERVICE_URL: str = "http://integration:8004"
    CHAT_SERVICE_URL: str = "http://chat:8005"

    REDIS_URL: str = "redis://localhost:6379/0"

    # 速率限制
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_CHAT_PER_MINUTE: int = 30


settings = Settings()
