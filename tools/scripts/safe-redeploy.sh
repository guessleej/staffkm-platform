#!/usr/bin/env bash
# 安全重新部署 — 解決 "rebuild 後 502" 的歷史共業。
#
# 用法：
#   ./tools/scripts/safe-redeploy.sh ui agent              # dev：只 rebuild + recreate 指定服務
#   ./tools/scripts/safe-redeploy.sh --all                 # dev：全部 rebuild
#   ./tools/scripts/safe-redeploy.sh ui --no-build         # dev：只 recreate，不重 build
#   ./tools/scripts/safe-redeploy.sh --prod --all          # v2.2：production overlay + .env.production
#
# 邏輯：
#   1. 解析參數（要動的服務 + 是否 build）
#   2. docker compose build --parallel（若要 build）
#   3. docker compose up -d --force-recreate ${services}
#   4. **強制 recreate nginx**（這是歷史教訓：UI / gateway 重新分配 IP 後
#      nginx 的 upstream 不會 re-resolve；不 recreate 會 502）
#   5. wait-healthy + smoke check（curl /login → 200）
#
# 退出碼：
#   0 = 成功，所有服務 healthy + smoke 通過
#   1 = build / up 失敗
#   2 = wait-healthy timeout
#   3 = smoke check failed

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

NO_BUILD=0
ALL=0
PROD=0
SERVICES=()

for a in "$@"; do
  case "$a" in
    --no-build)  NO_BUILD=1 ;;
    --all)       ALL=1 ;;
    --prod)      PROD=1 ;;
    -*)          echo "未知旗標：$a"; exit 1 ;;
    *)           SERVICES+=("$a") ;;
  esac
done

# v2.2：--prod 切到 production overlay + .env.production
if [ $PROD -eq 1 ]; then
  if [ ! -f .env.production ]; then
    echo "✗ .env.production 不存在；請 cp .env.production.example 並填值"
    exit 1
  fi
  echo "▶ 使用 production overlay (.env.production + docker-compose.production.yml)"
  COMPOSE=(docker compose --env-file .env.production \
    -f infra/docker-compose.yml \
    -f infra/docker-compose.production.yml \
    --project-directory .)
else
  COMPOSE=(docker compose --env-file .env -f infra/docker-compose.yml --project-directory .)
fi

# 預設可重 build 的服務集（staffkm/*）
ALL_BUILDABLE=(gateway auth knowledge knowledge-worker agent chat integration ui)

if [ $ALL -eq 1 ]; then
  SERVICES=("${ALL_BUILDABLE[@]}")
fi
if [ ${#SERVICES[@]} -eq 0 ]; then
  echo "用法：$0 <service> [<service> ...]   或   $0 --all"
  echo "可用服務：${ALL_BUILDABLE[*]}"
  exit 1
fi

echo "▶ 將處理：${SERVICES[*]}"

# 1) Build（除非 --no-build）
if [ $NO_BUILD -eq 0 ]; then
  # 過濾出真的能 build 的（embedder/postgres/nginx 等不 build）
  TO_BUILD=()
  for s in "${SERVICES[@]}"; do
    for b in "${ALL_BUILDABLE[@]}"; do
      if [ "$s" = "$b" ]; then TO_BUILD+=("$s"); break; fi
    done
  done
  if [ ${#TO_BUILD[@]} -gt 0 ]; then
    echo "▶ Building（parallel）：${TO_BUILD[*]}"
    "${COMPOSE[@]}" build --parallel "${TO_BUILD[@]}" || { echo "✗ build 失敗"; exit 1; }
  fi
fi

# 2) Recreate 指定服務
echo "▶ Recreating：${SERVICES[*]}"
"${COMPOSE[@]}" up -d --no-deps --force-recreate "${SERVICES[@]}" || { echo "✗ up 失敗"; exit 1; }

# 3) **關鍵教訓**：任何服務重啟，nginx 都必須跟著 recreate
#    否則 upstream IP 過時 → 502
echo "▶ Recreating nginx（強制 re-resolve upstream IP）"
"${COMPOSE[@]}" up -d --no-deps --force-recreate nginx || { echo "✗ nginx recreate 失敗"; exit 1; }

# 4) wait-healthy
echo "▶ 等待 services healthy（最多 90s）"
elapsed=0
while [ $elapsed -lt 90 ]; do
  bad=0
  for s in "${SERVICES[@]}" nginx; do
    cid=$("${COMPOSE[@]}" ps -q "$s" 2>/dev/null || true)
    if [ -z "$cid" ]; then continue; fi
    status=$(docker inspect -f '{{ .State.Health.Status }}' "$cid" 2>/dev/null || echo "starting")
    if [ "$status" != "healthy" ]; then bad=$((bad+1)); fi
  done
  if [ $bad -eq 0 ]; then echo "  ✓ all healthy in ${elapsed}s"; break; fi
  sleep 3; elapsed=$((elapsed+3))
done
if [ $elapsed -ge 90 ]; then
  echo "✗ 90s 內未全部 healthy"
  "${COMPOSE[@]}" ps
  exit 2
fi

# 5) Smoke check — / 與 /login 必須 200
sleep 1
for path in / /login; do
  code=$(curl -sw "%{http_code}" -o /dev/null "http://localhost${path}")
  if [ "$code" != "200" ]; then
    echo "✗ smoke check failed：GET $path → $code"
    exit 3
  fi
  echo "  ✓ GET $path → 200"
done

echo "✅ Redeploy 完成"
