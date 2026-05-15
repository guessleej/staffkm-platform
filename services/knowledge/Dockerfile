# context = 專案根目錄
FROM python:3.12-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 poppler-utils tesseract-ocr tesseract-ocr-chi-tra curl \
    antiword \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r staffkm && useradd -r -g staffkm staffkm

COPY services/knowledge/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM base AS runtime
COPY --chown=staffkm:staffkm services/knowledge/app ./app
COPY --chown=staffkm:staffkm core ./core

USER staffkm
EXPOSE 8001

HEALTHCHECK --interval=20s --timeout=5s --start-period=30s --retries=5 \
  CMD curl -sf http://localhost:8001/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "2"]
