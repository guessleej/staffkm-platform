# Multi-region readiness (v4.0)

> v4.0 落地 **active-passive** multi-region 基礎（P5 PG replica + P6 read routing + P7 MinIO secondary）。
> active-active（conflict resolution / CRDT / vector clock）排在 v5.0。

## 範圍

| 模組 | v3.x | v4.0 | v5.0+ |
|---|---|---|---|
| PG | single primary, daily pg_dump | + streaming replica (manual promote) | automated failover (patroni / pg_auto_failover) |
| App DB pool | 單 pool | + optional read pool, fallback 主 pool | per-region request routing |
| Object storage | single MinIO | + secondary MinIO (mc replicate rule) | active-active bucket replication |
| RTO / RPO | RTO ~30min / RPO 24h | **RTO < 5min / RPO < 1min** | RTO < 30s / RPO ≈ 0 |

---

## P5 — PostgreSQL streaming replication

### dev / staging（docker-compose）

```bash
# 起 replica（profile=multi-region）
docker compose --profile multi-region up -d postgres-replica

# host port 5433（避免跟 primary 5432 衝突）
psql -h localhost -p 5433 -U staffkm -d staffkm
```

⚠️ `infra/postgres/replica-init.sh` 只是 **demo placeholder**：
真實 streaming 還需要 `pg_basebackup` + replication slot + `primary_conninfo`。
本 init script 只把 `hot_standby = on` 設好，方便手動演練 promote。

### production 建議

| 環境 | 推薦做法 |
|---|---|
| K8s 自建 | [Patroni](https://github.com/patroni/patroni) operator（CrunchyData / Zalando） |
| K8s 自建（輕量） | [repmgr](https://www.repmgr.org/) on StatefulSet |
| AWS | RDS Multi-AZ + Aurora read replica |
| GCP | Cloud SQL HA + read replica |
| Azure | Flexible Server Zone-redundant HA |

本 chart 提供的 `templates/postgres-replica.yaml` 是給 demo / staging 用，
**不要在 production 直接 `replica.enabled=true`** 而沒設 streaming — 那只會起一個空的 pg 容器。

### Helm 啟用（demo only）

```yaml
# values.yaml
postgres:
  replica:
    enabled: true
    storage: "20Gi"
    storageClass: "gp3-encrypted"
```

```bash
helm upgrade --install staffkm ./infra/helm/staffkm -f my-values.yaml
```

### 升級到 v4.0 後的啟用步驟

1. 確認 primary `postgresql.conf` 已開 `wal_level=replica`、`max_wal_senders >= 5`
2. primary 建 replication user + slot：
   ```sql
   CREATE ROLE replicator WITH REPLICATION LOGIN PASSWORD '...';
   SELECT pg_create_physical_replication_slot('staffkm_replica_1');
   ```
3. replica 跑 `pg_basebackup -h primary -U replicator -D $PGDATA -Fp -Xs -P -R --slot=staffkm_replica_1`
4. 起 replica container/pod
5. 設 `DB_READ_URL` env（P6）讓報表流量開始走 replica

---

## P6 — Read replica routing

### env

```bash
# 不設 → 維持單 pool 行為（v3.x compatible）
DB_READ_URL=

# 設了 → admin_billing 等 read-only endpoint 自動走 replica
DB_READ_URL=postgresql+asyncpg://staffkm:secret@postgres-replica:5432/staffkm?ssl=disable
```

實作位置：`packages/python/staffkm-core/staffkm_core/utils/database.py`
- `init_db(db_url, read_url=None)` — read_url 不設則 read pool fallback 主 pool
- `get_read_session()` — read-only FastAPI dep，不會 commit、直接 close

agent service：`services/agent/app/main.py` lifespan 已自動帶 `settings.DB_READ_URL`。

### 已套用的 endpoint（v4.0 P6 示範）

`services/agent/app/api/admin_billing.py` 三個 endpoint：

- `GET /api/v1/admin/billing/users`
- `GET /api/v1/admin/billing/users/{user_id}`
- `GET /api/v1/admin/billing/users.csv`

純報表、跨月聚合、不寫資料 — 走 replica 風險最低，replication lag < 1s 對使用者無感。

### 想擴大用 read pool

把目標 endpoint 的 `Depends(get_session)` 換成 `Depends(get_read_session)`：

```python
from staffkm_core.utils.database import get_read_session

@router.get(...)
async def my_readonly_endpoint(
    session: AsyncSession = Depends(get_read_session),  # v4.0 P6
):
    ...
```

⚠️ 篩選 endpoint 時注意：
- 任何 `session.add(...)` / `session.execute(INSERT/UPDATE/DELETE)` **不要** 走 read pool
- `get_read_session` 不 commit；若有寫入路徑會跑出 `read-only transaction` 錯
- 一個 request 內混用 read + write session 是 OK 的（兩個獨立 dep）

預估候選：`/admin/heartbeats`、`/admin/quotas` 報表頁、`/analytics/*`、knowledge `/search`、`/hit-test` 等。
**v4.0 範圍不擴大**，等 v4.1 個別評估。

---

## P7 — MinIO secondary

### dev / staging（docker-compose）

```bash
docker compose --profile multi-region up -d minio-secondary
# console: http://localhost:9101  (root: staffkm / staffkm_minio)
# API:     http://localhost:9100
```

### 設定 bucket replication（一次性）

```bash
# 先在 primary 註冊 secondary 為 remote target
mc alias set primary   http://minio:9000          $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD
mc alias set secondary http://minio-secondary:9000 $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD

mc admin replicate add primary secondary    # site replication（雙向 metadata sync）

# 或單純 bucket-level 單向 sync
mc replicate add primary/staffkm-docs \
    --remote-bucket http://minio-secondary:9000/staffkm-docs \
    --replicate "delete,delete-marker,existing-objects"
```

production 把上面兩台換成 cross-region MinIO cluster / S3 cross-region replication（CRR）。

### Failover

- primary MinIO 掛 → 改 app `MINIO_ENDPOINT=minio-secondary:9000`
- 預設 read-only mount 到 secondary 避免雙寫；確認 primary 真的死再 promote
- RPO ≈ replication lag（同 region < 1s；cross-region 5-30s）

---

## RTO / RPO 目標

| 故障場景 | RTO | RPO | 備註 |
|---|---|---|---|
| PG primary 掛（有 replica） | < 5min | < 1min | manual promote + DSN 切換 |
| MinIO primary 掛 | < 5min | < 30s | mc alias 切換 |
| 整個 region 掛 | < 30min | < 5min | DNS / LB 切到 DR region |

v5.0 目標：active-active → RTO < 30s / RPO ≈ 0。

---

## 參考

- `infra/docker-compose.yml` — `postgres-replica` / `minio-secondary` services (profile `multi-region`)
- `infra/postgres/replica-init.sh` — demo init script
- `infra/helm/staffkm/templates/postgres-replica.yaml` — replica StatefulSet
- `infra/helm/staffkm/values.yaml` — `postgres.replica.*`
- `packages/python/staffkm-core/staffkm_core/utils/database.py` — `init_db()` / `get_read_session()`
- `services/agent/app/api/admin_billing.py` — 三個示範 endpoint
- `docs/deploy/dr-drill.md` — 場景 2 PG failover 步驟
