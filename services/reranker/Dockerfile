FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r reranker && useradd -r -g reranker reranker
COPY services/reranker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=reranker:reranker services/reranker/app ./app
USER reranker
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
  CMD curl -sf http://localhost:8000/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
