# Disaster Recovery Drill — v3.6

> 4 個場景的災難恢復演練步驟。建議**每季跑一次**確認 runbook 仍可用。

| 場景 | 平均 RTO | 平均 RPO |
|---|---|---|
| K8s rolling update | < 60s | 0 (graceful) |
| PostgreSQL primary failover | 1-2 min | < 30s (WAL replication) |
| Redis 重啟 | < 30s | 整個 cache + CAPTCHA counter 重置 |
| Backup full restore | 10-30 min | 最後一次 backup (24h) |

---

## 場景 1：K8s rolling update

### 預期行為
- `helm upgrade staffkm ./helm/staffkm` 觸發 rolling update
- agent service 收 SIGTERM → v3.6-P4 graceful shutdown 啟動：
  1. 等 `event_trigger_runs.status='running'` 全 done（最長 30s）
  2. cancel 5 個背景 worker
  3. 收 SIGKILL（compose `stop_grace_period: 60s` 留 60s 緩衝）
- 新 pod 啟動 → alembic upgrade head → 5 個 worker 重起

### 驗證步驟
```bash
# 1. 故意起一個長 workflow（含 wait node 60s）
curl -X POST .../api/v1/.../runs -d '...'  # 拿 run_id

# 2. 立刻觸發 rollout
kubectl rollout restart deployment/staffkm-agent

# 3. 觀察 log：應看到
# "agent_service_shutting_down"
# "graceful_shutdown_waiting" running=1
# "graceful_shutdown_no_inflight"  (或 30s timeout warning)

# 4. 新 pod 起來 → run 完成（status='ok'，沒卡 paused/error）
```

### Rollback
```bash
helm rollback staffkm <previous-revision>
```

---

## 場景 2：PostgreSQL primary failover

### 預期行為
- Primary PG 掛 → 連線錯
- pgBouncer / app 連線 retry → 切到 replica（需 promote）
- 升 v3.6 後 5 個 worker 都用 `FOR UPDATE SKIP LOCKED`，重連後自然繼續

### 演練步驟（dev / staging）
```bash
# 1. 模擬 primary 掛
docker stop staffkm-postgres
# 或 K8s: kubectl delete pod postgres-primary-0

# 2. promote replica（如有設定 patroni / repmgr）
kubectl exec postgres-replica-0 -- pg_ctl promote
# 或手動 pgsql: SELECT pg_promote();

# 3. update DSN 指向 new primary
kubectl set env deployment/staffkm-agent DB_URL=postgresql+asyncpg://...

# 4. 驗證
kubectl logs -f deployment/staffkm-agent | grep heartbeat
# 5 個 worker 應在 1 分鐘內恢復 beat
```

### 注意
- 沒設 streaming replication → RPO = 最後 backup 時間（24h）
- v3.6-P2 task_heartbeats 表會顯示 stale，admin /admin/heartbeats 看
- workflow_run_steps 可能 partial 寫入；無 transaction 確保 idempotent，但 step_index 不會跳號（INSERT 失敗就漏）

### v4.0 P5 — 有 replica 後的演練（active-passive）
v4.0 起 compose / Helm 都有 `postgres-replica`（預設關，profile=multi-region / `postgres.replica.enabled=true`）。
啟用後 PG primary 掛時可走以下 manual promote 流程（RTO < 5min）：

```bash
# 0. 確認 replica 正在跟 primary 同步（lag 多少）
docker exec staffkm-postgres-replica \
    psql -U staffkm -c "SELECT now() - pg_last_xact_replay_timestamp() AS lag;"

# 1. primary 已掛，promote replica
docker exec staffkm-postgres-replica \
    psql -U staffkm -c "SELECT pg_promote();"
# K8s: kubectl exec staffkm-postgres-replica-0 -- pg_ctl promote -D /var/lib/postgresql/data/pgdata

# 2. 切 app DSN 到 new primary（compose 改 DB_URL；K8s set env）
#    若已設 DB_READ_URL (v4.0 P6)，也記得換到一個還活著的 replica，否則先清空 fallback 到主 pool

# 3. 驗證
curl -sf http://staffkm.local/api/v1/health
# 5 個 worker 應在 1 分鐘內恢復 heartbeat
```

詳細設定看 `docs/deploy/multi-region.md`。production 仍建議走 patroni / managed PG（automated failover；v5.0+）。

---

## 場景 3：Redis 重啟

### 預期行為
- Redis 掛 → CAPTCHA 計數 fallback in-process（v3.0-P1 設計）
- agent / auth 服務不阻塞
- Redis 重啟後 → counter 從 0 開始（用戶體驗：失敗計次 reset）

### 演練
```bash
# 1. 模擬重啟
docker restart staffkm-redis

# 2. 驗證
curl -X POST .../api/v1/auth/login -d '{"username":"x","password":"wrong"}'
# 應該回 401（不是 500）

# 3. 連 4 次錯誤 → 不會立即觸發 captcha_required（counter 已重置）
```

### 影響
- CAPTCHA defense 暫時 degrade（in-process dict per replica）
- v3.4-P3 cross-encoder reranker 不受影響（不用 redis）
- Idempotency-Key 不受影響（用 PG 儲存）

---

## 場景 4：Backup full restore

### 預設備份策略
- `tools/backup/backup-postgres.sh` 每日 02:00 cron
- `tools/backup/backup-minio.sh` 每日 03:00 cron
- 保留 7 天

### 演練步驟
```bash
# 1. 模擬 disaster：清空 DB
docker exec staffkm-postgres psql -U staffkm -d staffkm -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# 2. 從最新 backup restore
ls -t tools/backup/dumps/staffkm-*.sql.gz | head -1
# /path/to/staffkm-2026-05-18.sql.gz

gunzip -c staffkm-2026-05-18.sql.gz | docker exec -i staffkm-postgres psql -U staffkm -d staffkm

# 3. restart services
docker compose restart agent auth knowledge chat

# 4. alembic 自動 upgrade head（包含 backup 之後新加的 migration）
docker logs staffkm-agent | grep alembic

# 5. 驗證
curl http://localhost/api/v1/health → 200
admin 登入、看 audit-logs → 應顯示 restore 前的最新紀錄
```

### 影響評估
- RPO：最差 24h（看 backup 跑點）
- workflow_run_steps / model_usage_logs / audit_logs 等如有 partition：要分別 restore each partition
- MinIO 上傳檔（文件 / image-gen output）：需另外 restore MinIO bucket

---

## 場景 4b：自動 backup-verify（v5.12 — **真跑、可重複**）

把場景 4 的「backup 能不能還原」從「相信 runbook」變成「機器跑過、md5 對得上」。

```bash
./tools/backup/dr-drill.sh            # ephemeral 容器：seed → pg_dump → 全新 host pg_restore → 驗證
ROWS=20000 ./tools/backup/dr-drill.sh # 自訂筆數
```

驗證 = **行數 + 內容 md5 + pgvector 向量** 三者一致才 PASS（退出碼 0）。用的是 `backup-postgres.sh`/
`restore-postgres.sh` 背後同一套 `pg_dump -Fc` / `pg_restore` 機制。

**v5.12 實測**（本機 pgvector:pg16，5000 筆含 vector(3)）：

| 項 | 值 |
|---|---|
| dump 大小 | 44 KB |
| pg_dump | < 1s |
| pg_restore（全新 host） | 1s |
| 行數一致 | 5000 = 5000 ✅ |
| 內容 md5 一致 | `6493e33…` = `6493e33…` ✅ |
| pgvector 還原 | `emb[id=42] = [42,42,42]` ✅ |
| **結果** | **PASS** |

⇒ backup→restore 機制**經實證可完整還原**（含向量），不是「設計上應該可以」。建議排進季度演練 + CI（self-hosted runner）。

---

## 後續演練計畫（v3.7+）

| 場景 | 目標 | 狀態 |
|---|---|---|
| 自動 backup verify（restore to ephemeral PG）| 確認 backup 可用 | ✅ **v5.12 真跑**（`tools/backup/dr-drill.sh`，場景 4b）|
| Active-active multi-region | < 5s RTO、0 RPO | ⏳ 需 ≥2 真實區域 DB 叢集（雲端 infra）；runbook 見 `docs/deploy/active-active.md`，**本機無法真跑 failover、不假裝** |
| Hot standby PG（streaming replication）| RPO < 1s | ⏳ 需 managed PG / patroni；場景 2 v4.0-P5 有 manual promote runbook |
| Chaos drill（隨機 kill pod）| 確認任何單一元件掛都不影響整體 | ⏳ 需 K8s 叢集 + chaos-mesh |

> **誠實標註**：active-active 多區 failover 的「真跑」需要至少兩個跨區的真實 PG 叢集 +
> 流量導向層，單機環境**無法如實演練**——所以此處只把可在本機真跑的 backup-verify 做成
> 實證（場景 4b），其餘維持「可執行 runbook + 明確前置條件」，不產生假的「跑過」記錄。
