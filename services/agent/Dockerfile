# context = 專案根目錄
FROM python:3.12-slim AS base
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r staffkm && useradd -r -g staffkm staffkm
COPY services/agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM base AS runtime
COPY --chown=staffkm:staffkm services/agent/app ./app
COPY --chown=staffkm:staffkm services/agent/alembic ./alembic
COPY --chown=staffkm:staffkm services/agent/alembic.ini ./alembic.ini
COPY --chown=staffkm:staffkm packages/python/staffkm-core/staffkm_core ./staffkm_core
COPY --chown=staffkm:staffkm packages/python/staffkm-tenant/staffkm_tenant ./staffkm_tenant
# v4.1 A: starter-pack 預設 application templates（admin install 用）
COPY --chown=staffkm:staffkm tools/starter-pack ./tools/starter-pack
USER staffkm
EXPOSE 8002
HEALTHCHECK --interval=20s --timeout=5s --start-period=30s --retries=5 \
  CMD curl -sf http://localhost:8002/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002", "--workers", "2"]
