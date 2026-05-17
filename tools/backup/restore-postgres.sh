#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════
#  restore-postgres.sh — 從 dump 還原（互動式 + 安全 confirm）
#
#  用法：
#    ./tools/backup/restore-postgres.sh                      # 列出所有 dump 讓選
#    ./tools/backup/restore-postgres.sh staffkm-20260517-0200.dump
#
#  ⚠️ 會 DROP + recreate database — 確認備份再執行
# ════════════════════════════════════════════════════════════════

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

if [ -f .env.production ]; then
  set -a; source .env.production; set +a
elif [ -f .env ]; then
  set -a; source .env; set +a
fi

DB_NAME="${DB_NAME:-staffkm}"
DB_USER="${DB_USER:-staffkm}"
BACKUP_DIR_HOST="${BACKUP_DIR:-/var/lib/staffkm/backups/postgres}"
BACKUP_DIR_CONTAINER="/backups"

# ── 選 dump ─────────────────────────────────────────
DUMP="${1:-}"
if [ -z "$DUMP" ]; then
  echo "可用的 dump：（newest 在上）"
  ls -1t "$BACKUP_DIR_HOST"/*.dump 2>/dev/null | head -10 | awk '{n=NR; print "  "n": "$0}'
  read -p "選 # 或貼檔名： " sel
  if [[ "$sel" =~ ^[0-9]+$ ]]; then
    DUMP=$(ls -1t "$BACKUP_DIR_HOST"/*.dump | sed -n "${sel}p")
  else
    DUMP="$BACKUP_DIR_HOST/$sel"
  fi
fi

if [ ! -f "$DUMP" ]; then echo "✗ 找不到 $DUMP"; exit 1; fi

DUMP_BASENAME=$(basename "$DUMP")
echo ""
echo "▶ 即將還原："
echo "   FROM: $DUMP"
echo "   TO:   database '$DB_NAME' (will DROP + recreate)"
echo ""
read -p "確定？敲 RESTORE 大寫繼續： " confirm
if [ "$confirm" != "RESTORE" ]; then echo "中止"; exit 0; fi

# ── 把 dump copy 到 postgres container ───────────────
docker cp "$DUMP" "staffkm-postgres:${BACKUP_DIR_CONTAINER}/${DUMP_BASENAME}"

# ── DROP + recreate（避免 own table conflict）────────
# 先 kill 所有連線
docker exec -e PGPASSWORD="${DB_PASSWORD}" staffkm-postgres \
  psql -U "$DB_USER" -d postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$DB_NAME' AND pid <> pg_backend_pid();"

docker exec -e PGPASSWORD="${DB_PASSWORD}" staffkm-postgres \
  psql -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS \"$DB_NAME\";"
docker exec -e PGPASSWORD="${DB_PASSWORD}" staffkm-postgres \
  psql -U "$DB_USER" -d postgres -c "CREATE DATABASE \"$DB_NAME\";"

# ── pg_restore — 平行 jobs 加速 ──────────────────────
echo "▶ pg_restore（並行 4 jobs）"
docker exec -e PGPASSWORD="${DB_PASSWORD}" staffkm-postgres \
  pg_restore -U "$DB_USER" -d "$DB_NAME" \
  --jobs=4 --no-owner --no-privileges \
  "${BACKUP_DIR_CONTAINER}/${DUMP_BASENAME}"

# ── verify ─────────────────────────────────────────
echo "▶ verifying"
COUNT=$(docker exec -e PGPASSWORD="${DB_PASSWORD}" staffkm-postgres \
  psql -U "$DB_USER" -d "$DB_NAME" -tAc \
  "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';")
echo "  tables in public schema: $COUNT"

echo ""
echo "✅ 還原完成。建議：safe-redeploy.sh agent gateway knowledge 重啟服務"
