#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════
#  replication-failover-drill.sh — PG streaming replication + failover「真跑」
#
#  active-active / active-passive 的**資料層** failover 演練（真跑，非 runbook 紙上談兵）：
#    primary → 串流複製 → standby → 殺 primary → pg_promote standby → 驗證可寫 + 資料完整。
#
#  ⚠ 真正的多區 active-active（雙寫 + CRDT 衝突解決）仍需雲端跨區 infra（見
#    docs/deploy/active-active.md）；CRDT 衝突解決語意由 services/agent/tests/test_crdt.py 守。
#    本檔涵蓋的是「單一寫入點 + 熱備 + 提升」這條可在本機真跑的 failover 路徑。
#
#  用法：./tools/backup/replication-failover-drill.sh
#  退出碼：0=PASS（複製+提升+資料完整），非 0=FAIL。
# ════════════════════════════════════════════════════════════════
set -euo pipefail

IMG="pgvector/pgvector:pg16"
NET=repl-drill-net
P=repl-drill-primary
R=repl-drill-replica

cleanup() { docker rm -f "$P" "$R" >/dev/null 2>&1 || true; docker network rm "$NET" >/dev/null 2>&1 || true; }
trap cleanup EXIT
cleanup

echo "[1/7] 起 primary（wal_level=replica + trust）"
docker network create "$NET" >/dev/null
docker run -d --name "$P" --network "$NET" \
  -e POSTGRES_USER=staffkm -e POSTGRES_PASSWORD=staffkm_secret -e POSTGRES_DB=staffkm \
  -e POSTGRES_HOST_AUTH_METHOD=trust "$IMG" \
  -c wal_level=replica -c max_wal_senders=10 -c hot_standby=on -c listen_addresses='*' >/dev/null
until docker exec "$P" pg_isready -U staffkm >/dev/null 2>&1; do sleep 1; done

echo "[2/7] 開 replication hba + 種資料"
# 官方 image 的 POSTGRES_HOST_AUTH_METHOD=trust 不含 replication 那條 → 補上 + reload
docker exec "$P" bash -c "echo 'host replication all all trust' >> /var/lib/postgresql/data/pg_hba.conf"
docker exec "$P" psql -U staffkm -d staffkm -qtAc "SELECT pg_reload_conf();" >/dev/null
docker exec "$P" psql -U staffkm -d staffkm -q -c \
  "CREATE TABLE t(id int primary key, v text); INSERT INTO t VALUES (1,'before-repl');"

echo "[3/7] 起 replica（pg_basebackup standby）"
docker run -d --name "$R" --network "$NET" --entrypoint bash "$IMG" -c '
  rm -rf /var/lib/postgresql/data/* ;
  until pg_isready -h '"$P"' -U staffkm >/dev/null 2>&1; do sleep 1; done ;
  pg_basebackup -h '"$P"' -U staffkm -D /var/lib/postgresql/data -Fp -Xs -R ;
  chown -R postgres:postgres /var/lib/postgresql/data ; chmod 700 /var/lib/postgresql/data ;
  exec gosu postgres postgres -c hot_standby=on -c listen_addresses=*
' >/dev/null
for _ in $(seq 1 30); do
  if [ "$(docker exec "$R" psql -U staffkm -d staffkm -tAc 'SELECT pg_is_in_recovery();' 2>/dev/null)" = "t" ]; then break; fi
  sleep 1
done
[ "$(docker exec "$R" psql -U staffkm -d staffkm -tAc 'SELECT pg_is_in_recovery();' 2>/dev/null)" = "t" ] \
  || { echo "❌ replica 未進入 standby"; exit 1; }

echo "[4/7] 驗證串流複製傳播"
docker exec "$P" psql -U staffkm -d staffkm -q -c "INSERT INTO t VALUES (2,'streamed');"
sleep 2
REPL_ROWS=$(docker exec "$R" psql -U staffkm -d staffkm -tAc "SELECT count(*) FROM t;")
[ "$REPL_ROWS" = "2" ] || { echo "❌ 複製沒傳播（replica rows=$REPL_ROWS）"; exit 1; }
LAG=$(docker exec "$R" psql -U staffkm -d staffkm -tAc \
  "SELECT COALESCE(EXTRACT(EPOCH FROM (now()-pg_last_xact_replay_timestamp()))::numeric(10,2),0);")
echo "      replica rows=$REPL_ROWS, lag=${LAG}s"

echo "[5/7] 驗證 standby 唯讀"
# 先收輸出再 grep（INSERT 預期失敗、psql 退非零；pipefail 下不能直接接 pipe）
RO_OUT=$(docker exec "$R" psql -U staffkm -d staffkm -tAc "INSERT INTO t VALUES (98,'x');" 2>&1 || true)
echo "$RO_OUT" | grep -qi 'read-only' || { echo "❌ standby 竟可寫: $RO_OUT"; exit 1; }

echo "[6/7] 殺 primary + 提升 replica"
docker stop "$P" >/dev/null
docker exec "$R" psql -U staffkm -d staffkm -qtAc "SELECT pg_promote();" >/dev/null
for _ in $(seq 1 15); do
  if [ "$(docker exec "$R" psql -U staffkm -d staffkm -tAc 'SELECT pg_is_in_recovery();' 2>/dev/null)" = "f" ]; then break; fi
  sleep 1
done

echo "[7/7] 驗證提升後可寫 + 資料完整"
docker exec "$R" psql -U staffkm -d staffkm -q -c "INSERT INTO t VALUES (3,'after-failover');"
FINAL=$(docker exec "$R" psql -U staffkm -d staffkm -tAc "SELECT count(*) FROM t;")
RECOV=$(docker exec "$R" psql -U staffkm -d staffkm -tAc "SELECT pg_is_in_recovery();")

if [ "$RECOV" = "f" ] && [ "$FINAL" = "3" ]; then
  echo "✅ Failover drill PASS — 複製傳播 + standby 唯讀 + promote 可寫 + 資料完整（$FINAL 筆）"
  exit 0
fi
echo "❌ Failover drill FAIL — recovery=$RECOV rows=$FINAL"
exit 1
