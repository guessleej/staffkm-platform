# context = 專案根目錄（monorepo build）
# ─────────────────────────────────────────────────────────────
#  Stage 1 — pnpm install（--frozen-lockfile 完全吃 pnpm-lock.yaml）+ 建置
#  改用 pnpm 取代 npm：npm install 不吃 pnpm-lock.yaml → ^ 浮動範圍 build 時
#  解析成最新版（曾因此把 typescript 拉到 5.9.3 撞爆 vue-tsc）。frozen-lockfile
#  鎖死整棵依賴樹、可重現。
#  ⚠ 關鍵：workspace 源碼套件（@staffkm/ui-kit / design-tokens，入口是 src/index.ts、
#    無 dist）的「源碼必須在 pnpm install 之前就位」，install 才會把 node_modules 連到
#    含 src 的真實目錄。若先只放 package.json 再裝，pnpm 會連到殘缺版 → vite 解析入口失敗。
# ─────────────────────────────────────────────────────────────
FROM node:22-alpine AS builder

WORKDIR /app

RUN corepack enable && corepack prepare pnpm@10.17.0 --activate

# workspace 定義 + lockfile
COPY pnpm-workspace.yaml pnpm-lock.yaml ./

# web 及其相依套件的「完整源碼」（入口 src/index.ts 需在 install 前就位）
COPY apps/web                  apps/web
COPY packages/ts/design-tokens packages/ts/design-tokens
COPY packages/ts/ui-kit        packages/ts/ui-kit

# 其餘 workspace 套件只需 manifest（--frozen-lockfile 需對齊 lockfile 內每個 package）
COPY apps/marketing/package.json          apps/marketing/package.json
COPY apps/docs/package.json               apps/docs/package.json
COPY apps/e2e/package.json                apps/e2e/package.json
COPY packages/ts/staffkm-sdk/package.json packages/ts/staffkm-sdk/package.json
COPY tools/e2e/package.json               tools/e2e/package.json

# 只裝 staffkm-ui（web）及其相依；frozen-lockfile 鎖死版本
RUN pnpm install --frozen-lockfile --filter staffkm-ui...

ARG VITE_API_BASE_URL=/api/v1
ARG VITE_APP_TITLE=StaffKM 行政知識管理系統
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_APP_TITLE=${VITE_APP_TITLE}

WORKDIR /app/apps/web
RUN pnpm build

# ─────────────────────────────────────────────────────────────
#  Stage 2 — Nginx
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
