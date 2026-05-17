#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════
#  backup-postgres.sh — daily pg_dump 到 backups volume / 外部 S3
#
#  用法（手動）：
#    ./tools/backup/backup-postgres.sh
#
#  Cron（daily 02:00）：
#    0 2 * * * cd /opt/staffkm && ./tools/backup/backup-postgres.sh >> /var/log/staffkm-backup.log 2>&1
#
#  保留策略：本機保留最近 14 份 daily + 8 份 weekly；S3 由 lifecycle policy 處理
# ════════════════════════════════════════════════════════════════

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

# ── 載入 env（產 prod 環境用 .env.production）──
if [ -f .env.production ]; then
  set -a; source .env.production; set +a
elif [ -f .env ]; then
  set -a; source .env; set +a
else
  echo "✗ 找不到 .env 或 .env.production"
  exit 1
fi

DB_NAME="${DB_NAME:-staffkm}"
DB_USER="${DB_USER:-staffkm}"
TS="$(date +%Y%m%d-%H%M)"
BACKUP_FILE="staffkm-${TS}.dump"
BACKUP_DIR_HOST="${BACKUP_DIR:-/var/lib/staffkm/backups/postgres}"
BACKUP_DIR_CONTAINER="/backups"

# 確保 host 目錄存在（給 docker volume mount）
mkdir -p "$BACKUP_DIR_HOST"

echo "▶ pg_dump → $BACKUP_FILE"

# pg_dump 用 custom format（-Fc）— 支援平行還原、選擇性 restore、壓縮
docker exec -e PGPASSWORD="${DB_PASSWORD}" staffkm-postgres \
  pg_dump -U "$DB_USER" -d "$DB_NAME" \
  --format=custom --compress=9 --no-owner --no-privileges \
  --file="${BACKUP_DIR_CONTAINER}/${BACKUP_FILE}"

# 取出來放 host
docker cp "staffkm-postgres:${BACKUP_DIR_CONTAINER}/${BACKUP_FILE}" "$BACKUP_DIR_HOST/${BACKUP_FILE}"
# 容器內也保留一份（重啟容器後 volume 還在）

SIZE=$(du -h "$BACKUP_DIR_HOST/${BACKUP_FILE}" | cut -f1)
echo "✓ $BACKUP_FILE ($SIZE)"

# ── 推 S3 / 對外 storage（可選）─────────────────────
if [ -n "${BACKUP_S3_URL:-}" ]; then
  echo "▶ uploading to $BACKUP_S3_URL"
  # 用 mc（minio client）也可上 S3 / 任何相容 endpoint
  docker run --rm \
    -v "$BACKUP_DIR_HOST:/in:ro" \
    -e MC_HOST_dest="$BACKUP_S3_URL" \
    minio/mc:latest \
    cp "/in/${BACKUP_FILE}" "dest/${BACKUP_FILE}"
fi

# ── 清舊備份 ─────────────────────────────────────────
# 保留：last 14 days + 每週日的
echo "▶ pruning old backups"
cd "$BACKUP_DIR_HOST"
ls -1t staffkm-*.dump 2>/dev/null | tail -n +15 | while read f; do
  # 保留週日的（dump 檔名 staffkm-YYYYMMDD-HHMM.dump）
  DATE_PART=$(echo "$f" | sed 's/staffkm-\([0-9]\{8\}\).*/\1/')
  DOW=$(date -j -f "%Y%m%d" "$DATE_PART" "+%u" 2>/dev/null || date -d "$DATE_PART" "+%u" 2>/dev/null)
  if [ "$DOW" = "7" ]; then continue; fi   # 週日 -> keep
  # 超過 8 週的週日也清
  AGE=$(( ( $(date +%s) - $(date -j -f "%Y%m%d" "$DATE_PART" "+%s" 2>/dev/null || date -d "$DATE_PART" "+%s" 2>/dev/null) ) / 86400 ))
  if [ "$AGE" -gt 56 ]; then rm -f "$f"; echo "  ✕ $f (age=${AGE}d)"; continue; fi
  rm -f "$f"; echo "  ✕ $f"
done

# ── 健康記號（給監控用）─────────────────────────────
touch "$BACKUP_DIR_HOST/.last-backup-success"
echo "✅ backup done $(date +%FT%T)"
