# v3 → v4 Upgrade Guide

> v4.0 是 major release，包含 breaking changes。**直接 v2.x → v4.0 不支援**。

---

## Pre-flight checklist

- [ ] 目前版本 ≥ v3.1（必要：alembic baseline 必須跑過至少一次）
- [ ] 確認沒有 client 還在打 `/api/v1/{prefix}/...` legacy URL（v4.0 移除 LegacyURLBridge）
- [ ] DB backup 已備（`tools/backup/backup-postgres.sh`）
- [ ] Staging 環境跑過 v4.0-rc1 至少 1 週

---

## Breaking changes 清單

| 變更 | 影響 | 對應 PR |
|---|---|---|
| 移除 `bootstrap_ddl.py` | v3.1 以下 deploy 直升會缺欄位 | #230 |
| 移除 `LegacyURLBridge` | 舊 SDK / curl 打 `/api/v1/{prefix}` 拿 404 | #231 |
| `init_db(read_url=...)` 新 signature | optional，舊 caller 不影響 | #234 |
| `WORKER_BACKEND` env 預設仍 `inprocess` | 不啟用 arq 行為不變 | #232 |

---

## 升級步驟（standard deploy）

### Step 1 — 升 v3.8 並驗證
```bash
docker compose pull
docker compose up -d
docker compose logs -f agent | grep alembic
# 確認 alembic 跑到 0014_slow_query_explains
```

### Step 2 — 驗證 0 legacy URL caller
```bash
# Loki / Grafana 查 v3.6 起的 legacy_url_blocked_410 log
# 應該長時間都是 0
```

### Step 3 — 升 v4.0
```bash
git pull
docker compose pull
docker compose down
docker compose up -d
```

升級過程：
- alembic 自動跑 `0002_*_schema_promoted`（IF NOT EXISTS，no-op for 已升過 deploy）
- LegacyURLBridge 移除 — 任何 v1 URL → 404
- Worker 仍預設 in-process（v3.x 行為）

### Step 4 — 驗證
```bash
curl http://localhost/api/v1/health
curl -H "X-Workspace-ID: <UUID>" http://localhost/api/v1/tools  # gateway proxy 注入
# 確認都 200
```

---

## Opt-in v4.0 新功能

### Distributed workers (arq)

```bash
# .env 加
echo "WORKER_BACKEND=arq" >> .env

# 啟動 worker container
docker compose --profile arq-worker up -d

# 驗證
curl http://localhost/api/v1/admin/workers/backend -H "Authorization: Bearer ..."
# → {"backend": "arq"}
curl http://localhost/api/v1/admin/workers/queue -H "Authorization: Bearer ..."
# → {"backend": "arq", "queue_depth": 0}
```

K8s：
```bash
helm upgrade staffkm ./infra/helm/staffkm \
    --set worker.enabled=true \
    --set agent.env.WORKER_BACKEND=arq
```

### Multi-region (PG read replica + MinIO secondary)

```bash
# 1. 啟 multi-region profile
docker compose --profile multi-region up -d postgres-replica minio-secondary

# 2. 設 read replica DSN
echo "DB_READ_URL=postgresql+asyncpg://staffkm:...@postgres-replica:5432/staffkm" >> .env

# 3. restart agent
docker compose restart agent

# 4. 驗證
docker logs staffkm-agent | grep read_pool
```

詳見 `docs/deploy/multi-region.md`。

---

## Rollback

### Rollback v4.0 → v3.8
**可行**（schema 仍兼容）：
```bash
git checkout v3.8.0
docker compose pull
docker compose up -d
```

### Rollback v4.0 → v3.7 或更早
**不可行**：v4.0 alembic chain (auth `0002` / knowledge `0002`) 沒有對應 downgrade path（schema 不變但 baseline marker 已寫入）。需手動 SQL revert `alembic_version` 表。

---

## 常見問題

### Q: 升 v4.0 後 curl 打 `/api/v1/tools` 拿 404，之前是 410
A: 預期行為。LegacyURLBridge 移除，必須改打 `/api/v1/workspace/{ws}/tools` 或帶 `X-Workspace-ID` header（gateway 會自動注入到 target URL）。

### Q: WORKER_BACKEND=arq 啟用後 in-process worker 還在跑？
A: 不會，agent lifespan 看到 env=arq 就跳過 `asyncio.create_task`。但 in-process loop 跟 arq worker **不能同時跑**（兩邊都會 claim queued runs）。確認 agent service log 有 `worker_backend_arq_inprocess_disabled`。

### Q: PG replica 怎麼 promote？
A: 詳見 `docs/deploy/dr-drill.md` 場景 2（v4.0 更新版本）— 手動 promote 步驟（`pg_promote()` + 切 DSN）。

### Q: 升完 v4.0 後 schema 怎麼變？
A: 變更：
- `users.oidc_sub` / `oidc_issuer` (auth 0002 promoted，舊 deploy 已有)
- 28 條 knowledge schema (knowledge 0002 promoted，舊 deploy 已有)
- 沒有新欄位（全是把 bootstrap_ddl 固化進 alembic）

---

## 下一步：v4.1+

- v4.1：AI-generated workflow
- v4.2：Stripe billing integration（SaaS）
- v4.3：Workflow marketplace
- v5.0：Active-active multi-region（CRDT）
