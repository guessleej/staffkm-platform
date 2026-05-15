# context = 專案根目錄（monorepo build）
# ─────────────────────────────────────────────────────────────
#  Stage 1 — 安裝依賴
# ─────────────────────────────────────────────────────────────
FROM node:22-alpine AS deps

WORKDIR /app

# 先複製 web app 的 manifest 與 workspace 套件 manifest
COPY apps/web/package.json                       apps/web/package.json
COPY packages/ts/design-tokens/package.json      packages/ts/design-tokens/package.json
COPY packages/ts/ui-kit/package.json             packages/ts/ui-kit/package.json

# 用 npm 直接裝 web app（workspace 套件以 file: 解析）
WORKDIR /app/apps/web
RUN npm install --prefer-offline --no-audit --no-fund

# ─────────────────────────────────────────────────────────────
#  Stage 2 — 建置靜態資源
# ─────────────────────────────────────────────────────────────
FROM node:22-alpine AS builder

WORKDIR /app

# 帶過 deps 階段的 node_modules + workspace 套件
COPY --from=deps /app /app
COPY apps/web                  /app/apps/web
COPY packages/ts/design-tokens /app/packages/ts/design-tokens
COPY packages/ts/ui-kit        /app/packages/ts/ui-kit

ARG VITE_API_BASE_URL=/api/v1
ARG VITE_APP_TITLE=StaffKM 行政知識管理系統
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_APP_TITLE=${VITE_APP_TITLE}

WORKDIR /app/apps/web
RUN npm run build

# ─────────────────────────────────────────────────────────────
#  Stage 3 — Nginx
# ─────────────────────────────────────────────────────────────
FROM nginx:1.27-alpine AS runtime

RUN rm /etc/nginx/conf.d/default.conf
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/apps/web/dist /usr/share/nginx/html

RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chmod -R 755 /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=20s --timeout=5s --retries=3 \
  CMD wget -qO- http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
