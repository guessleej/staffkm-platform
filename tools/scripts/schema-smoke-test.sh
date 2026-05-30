#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════════
#  Release smoke test：全新部署 schema 與升級路徑一致性
# ════════════════════════════════════════════════════════════════════════════
#  做三件事（只需 docker，不用起整套 stack）：
#   1. 用 init.sql 起一個全新 PG（模擬「全新部署」）。
#   2. 在其上跑 upgrade.sql → **每條加法 DDL 都必須被 skip（already exists）**。
#      若有任何 ALTER/CREATE 真的做了事 → init.sql 缺了該 delta（fresh ≠ upgraded）→ FAIL。
#      （這正是「只改 upgrade.sql 忘了同步 init.sql」的反向漂移守衛。）
#   3. 再跑一次 upgrade.sql → 必須一樣乾淨（idempotency；ON_ERROR_STOP 下重跑不炸）。
#
#  用法：tools/scripts/schema-smoke-test.sh   （exit 0 = PASS）
# ════════════════════════════════════════════════════════════════════════════
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
C=skm-schema-smoke
IMG=pgvector/pgvector:pg16

cleanup() { docker rm -f "$C" >/dev/null 2>&1 || true; }
trap cleanup EXIT
cleanup

echo "▶ 起全新 PG（init.sql 模擬全新部署）…"
docker run -d --name "$C" \
  -e POSTGRES_USER=staffkm -e POSTGRES_PASSWORD=smoke -e POSTGRES_DB=staffkm \
  -v "$ROOT/infra/postgres/init.sql:/docker-entrypoint-initdb.d/01_init.sql:ro" \
  "$IMG" >/dev/null

# 等 init.sql 跑完（entrypoint 會先以暫時 server 跑完 initdb 腳本才開正式 server）
for _ in $(seq 1 90); do
  docker exec "$C" pg_isready -U staffkm -d staffkm >/dev/null 2>&1 && break
  sleep 1
done
sleep 2

run_upgrade() {
  docker exec -i "$C" psql -U staffkm -d staffkm -v ON_ERROR_STOP=1 -f - \
    < "$ROOT/infra/postgres/upgrade.sql" 2>&1
}

echo "▶ 第 1 次 upgrade.sql（全新 init.sql DB 上應全 no-op）…"
OUT1="$(run_upgrade)"
echo "$OUT1" | sed 's/^/    /'

# 只數真正的 DDL 語句（排除 -- 註解行，否則註解裡的關鍵字會被誤算）
STMTS=$(grep -vE '^[[:space:]]*--' "$ROOT/infra/postgres/upgrade.sql" \
  | grep -cE 'ADD COLUMN IF NOT EXISTS|CREATE (UNIQUE )?INDEX IF NOT EXISTS')
SKIPS=$(printf '%s' "$OUT1" | grep -ci 'already exists, skipping' || true)

if [ "$SKIPS" -lt "$STMTS" ]; then
  echo "✗ FAIL：upgrade.sql 有 $STMTS 條加法 DDL，但全新 init.sql DB 上只 skip 了 $SKIPS 條。"
  echo "   → 某條 delta 不在 init.sql（全新部署會缺該欄/索引）。請把它**同步補進 init.sql**。"
  exit 1
fi

echo "▶ 第 2 次 upgrade.sql（idempotency 重跑）…"
run_upgrade >/dev/null
echo "✅ PASS：upgrade.sql 在全新 init.sql DB 上全 no-op（$SKIPS/$STMTS skip）且可重複執行。"
