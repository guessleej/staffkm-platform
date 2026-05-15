# ─────────────────────────────────────────────────────────────
#  Stage 1 — 安裝依賴（利用 Docker layer cache）
# ─────────────────────────────────────────────────────────────
FROM node:22-alpine AS deps

WORKDIR /app
COPY package.json ./
RUN npm install --prefer-offline

# ─────────────────────────────────────────────────────────────
#  Stage 2 — 建置靜態資源
# ─────────────────────────────────────────────────────────────
FROM node:22-alpine AS builder

WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

ARG VITE_API_BASE_URL=/api/v1
ARG VITE_APP_TITLE=StaffKM 行政知識管理系統

ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_APP_TITLE=${VITE_APP_TITLE}

RUN npm run build

# ─────────────────────────────────────────────────────────────
#  Stage 3 — 最終映像（Nginx 服務靜態檔案）
# ─────────────────────────────────────────────────────────────
FROM nginx:1.27-alpine AS runtime

# 移除預設設定
RUN rm /etc/nginx/conf.d/default.conf

# 複製 Nginx 設定
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 複製建置產物
COPY --from=builder /app/dist /usr/share/nginx/html

# 確保非 root 可讀取
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chmod -R 755 /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=20s --timeout=5s --retries=3 \
  CMD wget -qO- http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
