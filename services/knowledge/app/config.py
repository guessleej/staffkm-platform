from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DB_URL: str = "postgresql+asyncpg://staffkm:staffkm_secret@postgres:5432/staffkm?ssl=disable"
    REDIS_URL: str = "redis://:staffkm_redis@redis:6379/1"

    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "staffkm"
    MINIO_SECRET_KEY: str = "staffkm_minio"
    MINIO_BUCKET: str = "staffkm-docs"
    MINIO_SECURE: bool = False

    # Embedding 服務 — 預設指向內網 Ollama (bge-m3, 1024 維)
    # 若要改回 OpenAI：EMBEDDING_BASE_URL="" + EMBEDDING_MODEL=text-embedding-3-small + EMBEDDING_DIMENSION=1536
    EMBEDDING_MODEL: str = "bge-m3"
    EMBEDDING_BASE_URL: str = "http://embedder:11434/v1"
    EMBEDDING_DIMENSION: int = 1024
    OPENAI_API_KEY: str = ""

    # 文件分塊設定
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64
    MAX_FILE_SIZE_MB: int = 50

    # v5.9.19: 加 .xls (xlrd) + .html
    # v5.9.22: 加圖片 OCR (.png/.jpg/.jpeg/.webp/.tiff/.bmp)
    ALLOWED_EXTENSIONS: set[str] = {
        ".pdf", ".docx", ".doc", ".txt", ".md", ".xlsx", ".xls", ".csv", ".html",
        ".png", ".jpg", ".jpeg", ".webp", ".tiff", ".bmp",
    }


settings = Settings()
