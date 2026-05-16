#!/usr/bin/env bash
# 等待 docker compose stack 進入 healthy 狀態（CI / dev 共用）
#
# 使用：./tools/scripts/wait-healthy.sh [timeout_sec=180]
#
# - 預期 services: gateway / agent / knowledge / ui / nginx 健康後即返回 0
# - 任一 service unhealthy 超過 timeout → 印出 logs + 返回 1
set -euo pipefail

TIMEOUT=${1:-180}
SERVICES=(gateway agent knowledge chat auth nginx)

elapsed=0
while [ $elapsed -lt "$TIMEOUT" ]; do
  unhealthy=0
  for svc in "${SERVICES[@]}"; do
    cid=$(docker compose -f infra/docker-compose.yml ps -q "$svc" 2>/dev/null || true)
    if [ -z "$cid" ]; then continue; fi
    status=$(docker inspect -f '{{ .State.Health.Status }}' "$cid" 2>/dev/null || echo "starting")
    if [ "$status" != "healthy" ]; then
      unhealthy=$((unhealthy + 1))
    fi
  done
  if [ $unhealthy -eq 0 ]; then
    echo "✓ all services healthy in ${elapsed}s"
    exit 0
  fi
  sleep 5
  elapsed=$((elapsed + 5))
  echo "  …still waiting (${unhealthy} unhealthy, ${elapsed}/${TIMEOUT}s)"
done

echo "✗ timeout after ${TIMEOUT}s — dumping logs:"
docker compose -f infra/docker-compose.yml ps
docker compose -f infra/docker-compose.yml logs --tail=100
exit 1
