#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════
#  backup-minio.sh — MinIO bucket 鏡像備份
#
#  用法（手動）：
#    ./tools/backup/backup-minio.sh
#
#  Cron（daily 02:15）：
#    15 2 * * * cd /opt/staffkm && ./tools/backup/backup-minio.sh >> /var/log/staffkm-backup.log 2>&1
# ════════════════════════════════════════════════════════════════

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

if [ -f .env.production ]; then
  set -a; source .env.production; set +a
elif [ -f .env ]; then
  set -a; source .env; set +a
else
  echo "✗ 找不到 .env 或 .env.production"; exit 1
fi

MINIO_USER="${MINIO_ROOT_USER:-staffkm}"
MINIO_PW="${MINIO_ROOT_PASSWORD}"
BACKUP_DIR_HOST="${BACKUP_DIR:-/var/lib/staffkm/backups/minio}"
mkdir -p "$BACKUP_DIR_HOST"

TS="$(date +%Y%m%d-%H%M)"
DEST="$BACKUP_DIR_HOST/$TS"

echo "▶ MinIO mirror → $DEST"

# 用 mc client（官方鏡像）跑 mirror — 全部 buckets
docker run --rm \
  --network staffkm_backend \
  -v "$BACKUP_DIR_HOST:/backups" \
  -e MC_HOST_src="http://${MINIO_USER}:${MINIO_PW}@minio:9000" \
  minio/mc:latest \
  mirror --overwrite --remove src/ "/backups/$TS/"

SIZE=$(du -sh "$DEST" | cut -f1)
echo "✓ mirrored ($SIZE)"

# ── 推 S3（可選）──────────────────────────────────
if [ -n "${BACKUP_S3_URL:-}" ]; then
  echo "▶ uploading to $BACKUP_S3_URL"
  docker run --rm \
    -v "$BACKUP_DIR_HOST:/in:ro" \
    -e MC_HOST_dest="$BACKUP_S3_URL" \
    minio/mc:latest \
    mirror --overwrite "/in/$TS/" "dest/minio-$TS/"
fi

# ── 清舊（保留最近 14 份）────────────────────────────
echo "▶ pruning"
cd "$BACKUP_DIR_HOST"
ls -1t 2>/dev/null | grep -E '^[0-9]{8}-[0-9]{4}$' | tail -n +15 | while read d; do
  rm -rf "$d"; echo "  ✕ $d"
done

touch "$BACKUP_DIR_HOST/.last-backup-success"
echo "✅ minio backup done $(date +%FT%T)"
