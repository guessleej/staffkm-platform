#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════
#  dr-drill.sh — 災難復原演練「真跑」：seed → pg_dump → 全新 host 還原 → 驗證
#
#  驗證 tools/backup/{backup,restore}-postgres.sh 背後的 pg_dump/pg_restore 機制
#  能完整還原（含 pgvector 向量 + 內容 md5 一致），而非「設計上應該可以」。
#
#  用法：
#    ./tools/backup/dr-drill.sh            # 用 ephemeral 容器自我驗證（CI/本機）
#    ROWS=20000 ./tools/backup/dr-drill.sh # 自訂筆數
#
#  退出碼：0=PASS（行數+內容 md5+向量一致），非 0=FAIL。
# ════════════════════════════════════════════════════════════════
set -euo pipefail

ROWS="${ROWS:-5000}"
IMG="pgvector/pgvector:pg16"
PW="staffkm_secret"
SRC=dr-drill-src
DST=dr-drill-dst
DUMP="$(mktemp -t dr-drill.XXXXXX.dump)"

cleanup() { docker rm -f "$SRC" "$DST" >/dev/null 2>&1 || true; rm -f "$DUMP"; }
trap cleanup EXIT

_wait() { until docker exec "$1" pg_isready -U staffkm -d staffkm >/dev/null 2>&1; do sleep 1; done; }

echo "[1/5] 起 source + seed $ROWS 筆（含 pgvector）"
docker rm -f "$SRC" >/dev/null 2>&1 || true
docker run -d --name "$SRC" -e POSTGRES_USER=staffkm -e POSTGRES_PASSWORD="$PW" -e POSTGRES_DB=staffkm "$IMG" >/dev/null
_wait "$SRC"
docker exec "$SRC" psql -U staffkm -d staffkm -q -c "
  CREATE EXTENSION IF NOT EXISTS vector;
  CREATE TABLE paragraphs(id serial primary key, content text, emb vector(3));
  INSERT INTO paragraphs(content,emb)
    SELECT 'row '||g, ('['||g||','||g||','||g||']')::vector FROM generate_series(1,$ROWS) g;"
SRC_COUNT=$(docker exec "$SRC" psql -U staffkm -d staffkm -tAc "SELECT count(*) FROM paragraphs")
SRC_SUM=$(docker exec "$SRC" psql -U staffkm -d staffkm -tAc "SELECT md5(string_agg(content,',' ORDER BY id)) FROM paragraphs")
echo "      source rows=$SRC_COUNT md5=$SRC_SUM"

echo "[2/5] pg_dump（custom format，同 backup-postgres.sh）"
docker exec "$SRC" pg_dump -U staffkm -d staffkm -Fc -f /tmp/dr.dump
docker cp "$SRC:/tmp/dr.dump" "$DUMP" >/dev/null
echo "      dump=$(du -h "$DUMP" | cut -f1)"

echo "[3/5] 起 TARGET（全新 host，模擬 DR 機）"
docker rm -f "$DST" >/dev/null 2>&1 || true
docker run -d --name "$DST" -e POSTGRES_USER=staffkm -e POSTGRES_PASSWORD="$PW" -e POSTGRES_DB=staffkm "$IMG" >/dev/null
_wait "$DST"

echo "[4/5] pg_restore（同 restore-postgres.sh）"
docker cp "$DUMP" "$DST:/tmp/dr.dump" >/dev/null
docker exec "$DST" psql -U staffkm -d staffkm -q -c "CREATE EXTENSION IF NOT EXISTS vector;"
docker exec "$DST" pg_restore -U staffkm -d staffkm --no-owner /tmp/dr.dump

echo "[5/5] 驗證（行數 + 內容 md5 + 向量完整）"
DST_COUNT=$(docker exec "$DST" psql -U staffkm -d staffkm -tAc "SELECT count(*) FROM paragraphs")
DST_SUM=$(docker exec "$DST" psql -U staffkm -d staffkm -tAc "SELECT md5(string_agg(content,',' ORDER BY id)) FROM paragraphs")
DST_VEC=$(docker exec "$DST" psql -U staffkm -d staffkm -tAc "SELECT emb FROM paragraphs WHERE id=42")
echo "      target rows=$DST_COUNT md5=$DST_SUM vec[42]=$DST_VEC"

if [ "$DST_COUNT" = "$SRC_COUNT" ] && [ "$DST_SUM" = "$SRC_SUM" ]; then
  echo "✅ DR drill PASS — 行數 + 內容 md5 + pgvector 完整還原"
  exit 0
fi
echo "❌ DR drill FAIL — 還原後不一致"
exit 1
