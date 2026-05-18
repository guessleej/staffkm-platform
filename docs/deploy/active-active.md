# Active-Active Multi-Region Deployment

> 狀態：**架構文件 + scaffolding only**（v5.0 Theme K）。
> 真實 GA 流量切換等 v5.1+。
> 撰寫日期：2026-05-18

本文說明 staffKM 在多 region 同時可寫場景下的設計取捨、衝突來源、與三層
解法策略。閱讀前請先讀 [`docs/plans/v5.0-roadmap.md`](../plans/v5.0-roadmap.md)
了解整體計畫。

---

## 1. 為何 active-active 很難

v4.0 落地的 **active-passive multi-region**（PG streaming replica + read
routing + MinIO secondary）只解一半：

- ✅ 唯一寫節點：primary region；其他 region 只 forward write + 本地 read
- ✅ 故障切換：promote secondary → 新 primary（RTO 分鐘等級）
- ❌ 寫流量無法被多 region 同時吃 → 跨大洲 user 寫延遲很高

而 **active-active** 要求兩個（含以上）region 都能 **本地接寫**。這在 PostgreSQL
裡天生衝突：

| 衝突場景 | 為什麼難 |
|---|---|
| **同列同欄位被兩 region 同時改** | last-write-wins 必須仰賴可信時間源；wall clock skew 會 silently 吃掉寫入 |
| **同 unique key insert** | 兩 region 都 insert `users(email='x')` → replication 後撞 unique constraint |
| **foreign key 順序** | region A 先寫 parent、region B 先寫 child → 跨 region merge 看到 child 找不到 parent |
| **monotonic counter** | `quota.used += 1` 在兩 region 同時跑、merge 後不會自然相加（後寫覆蓋先寫） |
| **序號 / sequence** | PG sequence 各 region 獨立、collision 必然發生（要 region-pinned offset） |

關係型 DB 沒有「自動」的多寫節點解 — 必須在 application + DB 層共同設計。

---

## 2. 三層策略（v5.0 採納）

### L1 — Region-pinned writes（首選；簡單可靠）

**每個 workspace 綁一個 primary region**；其他 region 收到該 workspace 的寫
請求時，**308 redirect 回 primary**。

優點：
- 同一 workspace 的寫永遠只在一個節點 → 退化成 active-passive、無衝突
- 跨 region 的是 read（streaming replica 已支援）
- 用 workspace 邊界 colocate data：不同公司本來就在不同 region 是常態

代價：
- 全球 user 寫同一 workspace 仍要跨海來回（但比 active-passive 不糟）
- workspace 第一次釘 region 後要 migrate data 才能換

**v5.0 落實**：`workspace.primary_region` column + `RegionRouterMiddleware`
在收到寫請求時查 cache、不符就 308。

```
PUT  /api/v1/applications/x  → us-east (workspace primary)
                              ┌─ POST /api/v1/applications/x
EU client ──→ eu-west region ─┤
                              └─ 308 Location: https://us-east.staffkm.io/...
```

### L2 — Eventual consistency via logical replication

某些 **跨 workspace 的全域資料**（model registry / pricing / plugins）無法
用 L1 pin（每個 region 都要讀 + 偶爾 admin 寫）。對這類資料：

- 走 **PostgreSQL logical replication**（pglogical / native `CREATE PUBLICATION`）
- 寫永遠走 designated「source-of-truth region」（admin 後台所在）
- 其他 region 是 logical subscriber、read-only

**v5.0 不交付**這部分 ops 設定，因為它是 DBA 工作（取捨 publish slot、
WAL retention、subscriber lag alarm）。文件留 v5.5 ops playbook。

### L3 — CRDT for naturally mergeable state

少數 entity 是 **append-only / commutative**，可以多 region 同時寫、不衝突：

| Entity | 為何天然 CRDT | 解法 |
|---|---|---|
| `model_usage_logs` | 純 append（每筆 log 是新 row、不改舊 row） | 直接跨 region union；UUID PK 防撞 |
| `audit_logs` | 同上 | 同上 |
| `quota.used` | 只加不減（reset 是 admin 動作） | **G-Counter**：每個 region 維護自己的 partial count，read 時 sum |
| `ratings.upvote_count` | 只加 | 同上 |
| `app.tags[]` | set semantics | **OR-Set**（observed-remove set）才能解 add+remove 競態 |
| `workflow.current_state` | mutable LWW（最後一手贏） | **LWW-Register** + Lamport / hybrid clock |

**v5.0 只交 reference impl**（`app/core/crdt.py`：LWW + G-Counter stub），未接
hot path。v5.2 才把 `model_usage_logs` / `user_quotas` 真的接上跨 region merge。

---

## 3. 衝突偵測 + 解決 framework

當 logical replication apply 失敗（例如 unique constraint violation）或
CRDT merge 發現不可自動解的 case（例如 LWW 兩邊 timestamp 相同到 us 級）→
寫一筆到 `region_conflict_log`：

```sql
CREATE TABLE region_conflict_log (
    id              UUID PRIMARY KEY,
    detected_at     TIMESTAMPTZ,
    entity_type     VARCHAR(32),    -- 'rating' / 'usage' / 'quota' / 'workflow'
    entity_id       VARCHAR(64),
    region_a        VARCHAR(32),
    region_b        VARCHAR(32),
    value_a         JSONB,
    value_b         JSONB,
    resolution      VARCHAR(16),    -- 'lww' | 'merge' | 'manual' | 'pending'
    resolved_value  JSONB,
    resolved_at     TIMESTAMPTZ
);
```

Admin 走 `GET /api/v1/admin/conflicts?status=pending` 看待處理 conflict、
`POST /admin/conflicts/{id}/resolve` 寫死最終值。

v5.3 會做 side-by-side diff UI + 一鍵套用。

---

## 4. Region 註冊 + cluster topology

`regions` 表是 cluster-wide 的 registry：

```sql
CREATE TABLE regions (
    id              VARCHAR(32) PRIMARY KEY,     -- 'us-east-1' / 'eu-west-1'
    name            VARCHAR(64),
    db_url          TEXT,                         -- read DSN for this region
    minio_endpoint  TEXT,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ
);
```

每個 instance 啟動時讀 env `REGION_ID=us-east-1` 知道自己是誰。Redirect target
URL 從 env `REGION_<UPPERCASE_DASH_TO_UNDERSCORE>_URL` 讀（例如 `REGION_EU_WEST_1_URL`）。

> 用 env 而非 `regions.db_url` 推 URL，是因為 redirect 要 **公開可解 hostname**，
> 而 `db_url` 是 service-internal DSN。兩件事不同。

---

## 5. 為何 v5.0 **不** 真接 production active-active

下列每一項都是大量 ops 工作、單純程式碼層交付無意義：

1. **Multi-region PG**：需 Aurora Global / Citus / pglogical 三選一 + 跨海
   WAN 帶寬 SLA + monitoring
2. **Conflict alarm**：要接 Prometheus + Slack/PagerDuty webhook + dedup
3. **Region failover testing**：要週期性 chaos drill 驗證 RTO
4. **Sequence collision**：要把所有 `bigserial` 換成 UUIDv7 或 region-offset
5. **Schema migration**：alembic 跨 region 跑會有 lock 序列、需 staged rollout

v5.0 提供 **架構 + framework**，v5.x 系列分階段補 ops。

---

## 6. 在 v5.0 試 region routing（dev / staging）

```bash
# Region A (us-east-1)
docker compose up -d
# .env:
MULTI_REGION_ENABLED=true
REGION_ID=us-east-1
REGION_EU_WEST_1_URL=https://eu.staging.staffkm.local

# Region B (eu-west-1) — 另一台
docker compose up -d
# .env:
MULTI_REGION_ENABLED=true
REGION_ID=eu-west-1
REGION_US_EAST_1_URL=https://us.staging.staffkm.local

# 註冊 regions（其中一邊跑就好，假設兩邊同 DB cluster）
curl -X POST https://us.staging.staffkm.local/api/v1/admin/regions \
  -H "Authorization: Bearer ..." \
  -d '{"id":"us-east-1","name":"US East"}'
curl -X POST https://us.staging.staffkm.local/api/v1/admin/regions \
  -H "Authorization: Bearer ..." \
  -d '{"id":"eu-west-1","name":"EU West"}'

# 把 workspace 釘到 us-east-1
curl -X PUT https://us.staging.staffkm.local/api/v1/admin/workspaces/{wsid}/region \
  -d '{"primary_region":"us-east-1"}'

# 從 EU 寫 → 應收 308 Location: https://us.staging.staffkm.local/...
curl -X POST https://eu.staging.staffkm.local/api/v1/applications \
  -H "X-Workspace-ID: {wsid}" -d '{...}'
```

---

## 7. 觀測（v5.0 sketch）

未來 v5.1+ 加 Prometheus metrics（這裡只列）：

- `staffkm_region_redirect_total{from_region, to_region}` — counter
- `staffkm_region_conflict_total{entity_type, resolution}` — counter
- `staffkm_region_replication_lag_seconds{from_region, to_region}` — gauge
- `staffkm_region_conflict_pending` — gauge（unresolved backlog）

---

## 8. FAQ

**Q：可以不靠 workspace pin、純靠 CRDT 全域 active-active 嗎？**
A：理論可（CockroachDB / YugabyteDB 路線），但 staffKM 用 PG，要轉就是換 DB。
v5.x 不走那條路。

**Q：L1 redirect 對 SPA 體驗會不會很差？**
A：第一次 redirect 後 axios interceptor 可以 cache `workspace → region` 對應、
直接打對的 base URL。v5.1 frontend layer 會做。

**Q：MinIO 怎麼辦？**
A：MinIO 已有 site-replication；v4.0 已 active-passive。Active-active MinIO 需
`mc admin replicate add` + bucket versioning + 解 same-key conflict（MinIO 內
建 LWW）。文件留 v5.5。
