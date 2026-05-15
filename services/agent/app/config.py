from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DB_URL: str = "postgresql+asyncpg://staffkm:staffkm_secret@postgres:5432/staffkm?ssl=disable"
    REDIS_URL: str = "redis://:staffkm_redis@redis:6379/2"
    KNOWLEDGE_SERVICE_URL: str = "http://knowledge:8001"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    ANTHROPIC_API_KEY: str = ""
    MAX_CONTEXT_MESSAGES: int = 20


settings = Settings()
