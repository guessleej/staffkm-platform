# context = 專案根目錄
FROM python:3.12-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 poppler-utils tesseract-ocr tesseract-ocr-chi-tra tesseract-ocr-chi-sim curl \
    antiword \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r staffkm && useradd -r -g staffkm staffkm

COPY services/knowledge/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM base AS runtime
COPY --chown=staffkm:staffkm services/knowledge/app ./app
COPY --chown=staffkm:staffkm services/knowledge/alembic ./alembic
COPY --chown=staffkm:staffkm services/knowledge/alembic.ini ./alembic.ini
COPY --chown=staffkm:staffkm packages/python/staffkm-core/staffkm_core     ./staffkm_core
COPY --chown=staffkm:staffkm packages/python/staffkm-tenant/staffkm_tenant ./staffkm_tenant

# v5.12: 預先下載內建 reranker 模型到固定快取 → 離線可用、安裝即啟用。
#   download 失敗不擋 build（runtime warmup 會補下載）；主模型失敗退較小的 bge-reranker-base。
RUN mkdir -p /app/.fastembed_cache && \
    ( python -c "from fastembed.rerank.cross_encoder import TextCrossEncoder; TextCrossEncoder(model_name='BAAI/bge-reranker-base', cache_dir='/app/.fastembed_cache')" \
      || echo "reranker model bake deferred to runtime" ) && \
    chown -R staffkm:staffkm /app/.fastembed_cache

USER staffkm
EXPOSE 8001

HEALTHCHECK --interval=20s --timeout=5s --start-period=30s --retries=5 \
  CMD curl -sf http://localhost:8001/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "2"]
