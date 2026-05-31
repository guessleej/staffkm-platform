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

    # Embedding 服務 — 預設指向內網 Ollama (snowflake-arctic-embed2, 1024 維)
    # 若要改回 OpenAI：EMBEDDING_BASE_URL="" + EMBEDDING_MODEL=text-embedding-3-small + EMBEDDING_DIMENSION=1536
    EMBEDDING_MODEL: str = "snowflake-arctic-embed2"
    EMBEDDING_BASE_URL: str = "http://embedder:11434/v1"
    EMBEDDING_DIMENSION: int = 1024
    OPENAI_API_KEY: str = ""

    # ivfflat 近似向量搜尋掃描的倒排清單數（pgvector 預設 1 → 召回極差且對 embedding 微擾敏感）。
    # 建議 ≈ sqrt(lists)（索引 lists=100 → 10）。每條向量查詢以 SET LOCAL 套用（pooling 安全）。
    IVFFLAT_PROBES: int = 10

    # v5.12: 內建 in-process ONNX reranker（fastembed，無 torch / 無外部服務、模型已烤進 image）。
    #   **預設關**（off-by-default）：實測 bge-reranker-base 載入吃 ~1.9GB RAM，不強迫每客戶承擔。
    #   要啟用：RERANKER_DEFAULT_LOCAL=true + 把 knowledge 容器記憶體上限調 ≥3g（compose）。
    #   模型 = bge-reranker-base（fastembed 唯一「多語含中文 + Apache-2.0 可商用」選項；
    #   v2-m3 fastembed 不支援、jina-v2 多語 CC-BY-NC 不可商用）。要更強中文走外部 llama.cpp + v2-m3。
    RERANKER_DEFAULT_LOCAL: bool = False
    RERANKER_LOCAL_MODEL: str = "BAAI/bge-reranker-base"

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
    # Phase 2 多跳召回：錨定實體後沿 kb_relations 擴幾跳（0=關閉、1=一跳鄰居）。
    # 擴出的段落仍受融合端 graph-only cosine 門檻過濾 → 不引入噪音（A/B 實測 harm-free）。
    # 預設 0（關閉）：小型語料 A/B 實測多跳增益=+0.000 —— top-5 向量錨定已涵蓋相關實體，
    #   且關係多為「文件內共現」（鄰居與錨點共用段落）→ 多跳補不出新段落、徒增一次查詢。
    #   價值在「跨文件關係 + 較大語料（相關實體圖上連通但向量不相近）」浮現；屆時設 1 並用
    #   tools/eval/graphrag_ab.py 的 hop0-vs-hop1 驗證有增益再開。
    GRAPH_QUERY_HOPS: int = 0
    # D 社群入查詢：錨定實體 → 找其所屬 kb_communities → 展開整個社群成員的 mention 段落
    # （global-ish 召回訊號）。擴出段落仍受融合端 cosine 門檻過濾。**預設 False（關閉）**：
    #   小語料社群多為「文件內共現」→ 與多跳同理、無實測增益。價值在大語料 + 多跨文件叢集；
    #   屆時設 True 並用 graph_ab.py 的 community on/off 驗證有增益再開。
    GRAPH_QUERY_COMMUNITY: bool = False


settings = Settings()
