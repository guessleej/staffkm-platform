#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════
#  restore-minio.sh — 從備份目錄還原 MinIO bucket
#  用法：
#    ./tools/backup/restore-minio.sh                 # 列出選
#    ./tools/backup/restore-minio.sh 20260517-0215
# ════════════════════════════════════════════════════════════════

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

if [ -f .env.production ]; then
  set -a; source .env.production; set +a
elif [ -f .env ]; then
  set -a; source .env; set +a
fi

MINIO_USER="${MINIO_ROOT_USER:-staffkm}"
MINIO_PW="${MINIO_ROOT_PASSWORD}"
BACKUP_DIR_HOST="${BACKUP_DIR:-/var/lib/staffkm/backups/minio}"

SNAPSHOT="${1:-}"
if [ -z "$SNAPSHOT" ]; then
  echo "可用的快照："
  ls -1t "$BACKUP_DIR_HOST" | grep -E '^[0-9]{8}-[0-9]{4}$' | head -10 | awk '{n=NR; print "  "n": "$0}'
  read -p "選 # 或貼名： " sel
  if [[ "$sel" =~ ^[0-9]+$ ]]; then
    SNAPSHOT=$(ls -1t "$BACKUP_DIR_HOST" | grep -E '^[0-9]{8}-[0-9]{4}$' | sed -n "${sel}p")
  else
    SNAPSHOT="$sel"
  fi
fi

SRC="$BACKUP_DIR_HOST/$SNAPSHOT"
if [ ! -d "$SRC" ]; then echo "✗ 找不到 $SRC"; exit 1; fi

echo ""
echo "▶ 即將還原 MinIO:"
echo "   FROM: $SRC"
echo "   TO:   live MinIO（會覆蓋同 key）"
echo ""
read -p "確定？敲 RESTORE 繼續： " confirm
if [ "$confirm" != "RESTORE" ]; then echo "中止"; exit 0; fi

docker run --rm \
  --network staffkm_backend \
  -v "$BACKUP_DIR_HOST:/backups:ro" \
  -e MC_HOST_dest="http://${MINIO_USER}:${MINIO_PW}@minio:9000" \
  minio/mc:latest \
  mirror --overwrite "/backups/$SNAPSHOT/" dest/

echo ""
echo "✅ MinIO 還原完成"
