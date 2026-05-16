#!/usr/bin/env bash
# 從跑中的 service 抓 OpenAPI spec，輸出到 docs/openapi/
#
# 前置：docker compose up 後跑此腳本
set -euo pipefail

OUT_DIR="${OUT_DIR:-docs/openapi}"
mkdir -p "$OUT_DIR"

declare -A SERVICES=(
  [gateway]="http://localhost:8000/openapi.json"
  [auth]="http://localhost:8003/openapi.json"
  [knowledge]="http://localhost:8001/openapi.json"
  [agent]="http://localhost:8002/openapi.json"
  [chat]="http://localhost:8005/openapi.json"
)

for svc in "${!SERVICES[@]}"; do
  url="${SERVICES[$svc]}"
  echo "→ $svc  $url"
  if curl -fsSL "$url" -o "$OUT_DIR/$svc.json"; then
    echo "  ✓ $OUT_DIR/$svc.json"
  else
    echo "  ✗ failed ($url)"
  fi
done

echo
echo "Done. 可用以下指令產 client SDK："
echo "  npx @openapitools/openapi-generator-cli generate \\"
echo "    -i $OUT_DIR/agent.json -g typescript-axios -o tools/codegen/sdk-ts/agent"
