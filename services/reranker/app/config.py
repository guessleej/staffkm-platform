from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    MODEL_NAME:    str = "BAAI/bge-reranker-v2-m3"
    MODEL_DEVICE:  str = "cpu"           # 'cuda' if GPU available
    MAX_LENGTH:    int = 512
    BATCH_SIZE:    int = 32
    DEFAULT_TOP_N: int = 5


settings = Settings()
