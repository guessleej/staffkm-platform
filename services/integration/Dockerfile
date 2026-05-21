# context = 專案根目錄
FROM python:3.12-slim AS base
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r staffkm && useradd -r -g staffkm staffkm
COPY services/integration/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM base AS runtime
COPY --chown=staffkm:staffkm services/integration/app ./app
# v5.9.30: 補 staffkm_core — main.py import staffkm_core.observability，
# 之前漏 COPY → ModuleNotFoundError → crash loop
COPY --chown=staffkm:staffkm packages/python/staffkm-core/staffkm_core ./staffkm_core
USER staffkm
EXPOSE 8004
HEALTHCHECK --interval=20s --timeout=5s --start-period=30s --retries=5 \
  CMD curl -sf http://localhost:8004/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004"]
