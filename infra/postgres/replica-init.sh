#!/bin/bash
# v4.0 P5: Simple replica setup (dev/staging only — DEMO PLACEHOLDER)
#
# ⚠️  production 建議改用 patroni / repmgr / managed PG（RDS Multi-AZ）
# 真實 streaming replication 需 pg_basebackup + replication slot + primary_conninfo，
# 本 script 只在 replica container 第一次 init 跑，把 hot_standby 開起來方便手動 promote 演練。
set -e

echo "replica-init: configure replication-friendly defaults"

cat >> ${PGDATA}/postgresql.conf <<EOF
# v4.0 P5: streaming replication (replica side) — DEMO defaults
hot_standby = on
max_standby_archive_delay = 30s
max_standby_streaming_delay = 30s
EOF

echo "replica-init: done (production 須手動 pg_basebackup + slot 設定)"
