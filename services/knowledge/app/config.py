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
        ".odt", ".ods",   # v5.11.x: ODF（政府/教育公文常用 OpenDocument）
    }

    # v5.9.23: OCR 引擎切換
    #   "tesseract" (預設) — 地端 Tesseract LSTM，離線零費用
    #   "vision"           — Vision LLM OCR（預設也走地端 Ollama vision model）
    OCR_ENGINE: str = "tesseract"
    # Vision OCR：預設指向內網 Ollama（地端優先）。改 cloud 就換 base_url + api_key + model
    VISION_OCR_MODEL: str = "llama3.2-vision"
    VISION_OCR_BASE_URL: str = "http://embedder:11434/v1"
    VISION_OCR_API_KEY: str = ""   # 地端 Ollama 不需要；cloud (Kimi/OpenAI) 才填
    # Vision OCR 失敗 → 是否自動 fallback 回 Tesseract
    VISION_OCR_FALLBACK_TESSERACT: bool = True

    # ── RFC-014 GraphRAG 加法層（MVP v5.11.0）─────────────────────
    # 實體抽取 LLM：預設用地端 Ollama 既有的 gemma4:e4b（閒置中，零新下載/零雲端成本/
    # 無 Kimi content-filter）。要更高品質才切雲端（換 base_url + api_key + model）。
    GRAPH_EXTRACT_MODEL:    str = "gemma4:e4b"
    GRAPH_EXTRACT_BASE_URL: str = "http://embedder:11434/v1"
    GRAPH_EXTRACT_API_KEY:  str = "dummy"          # 地端 Ollama 不檢查
    # query→實體 比對：取相似度前 N 個實體，再 JOIN mentions 取候選段落
    GRAPH_QUERY_TOP_ENTITIES: int = 5


settings = Settings()
