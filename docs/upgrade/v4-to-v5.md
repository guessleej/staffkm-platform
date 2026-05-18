# Upgrade Guide: v4.x → v5.0

> 撰寫日期：2026-05-18
> **Major release** — 但 breaking 面實際很小，因為 v5.0 主交付是 scaffolding。

## TL;DR

```bash
git pull && git checkout v5.0.0
./tools/scripts/safe-redeploy.sh --all       # 起來、跑 alembic、沒事
```

預設不開 multi-region。行為與 v4.x 完全等同。

## Breaking changes

| 項目 | 影響 | 處理 |
|---|---|---|
| `alembic 0019_multi_region` revision 加入 | DB schema 加 1 欄 + 2 表 | lifespan 自動跑 alembic upgrade head；無 manual step |
| 沒有其他 breaking — `MULTI_REGION_ENABLED` 預設 `false` | — | — |

> 對比 v3 → v4：v4.0 拔了 bootstrap_ddl + LegacyURLBridge，遷移路徑緊張。
> v5.0 走 **additive only** — 全程可回滾（`alembic downgrade -1` 即可）。

## 升級步驟

### 0. 前置檢查

- 目前 deploy 必須 ≥ v4.0.0（alembic head = `0018_workflow_marketplace`）
- 備份：`./tools/backup/backup-postgres.sh`

### 1. 拉 v5.0 + redeploy

```bash
cd /path/to/staffKM
git fetch --tags && git checkout v5.0.0
./tools/scripts/safe-redeploy.sh --all
```

`safe-redeploy.sh` 會：
1. build new image
2. recreate container
3. agent service lifespan 跑 `alembic upgrade head` → 加 `workspace.primary_region`
   欄、`regions` 表、`region_conflict_log` 表
4. health probe 等服務 ready

### 2. 驗證

```bash
# alembic 在 head
docker exec staffkm-postgres psql -U staffkm -d staffkm \
  -c "SELECT version_num FROM alembic_version;"
# → 0019_multi_region

# 新欄位有
docker exec staffkm-postgres psql -U staffkm -d staffkm \
  -c "\d workspace" | grep primary_region

# 新表有
docker exec staffkm-postgres psql -U staffkm -d staffkm \
  -c "\dt regions"
docker exec staffkm-postgres psql -U staffkm -d staffkm \
  -c "\dt region_conflict_log"
```

### 3.（選擇性）試 multi-region routing

預設 `MULTI_REGION_ENABLED=false`。要試先讀
[`docs/deploy/active-active.md` §6](../deploy/active-active.md)。

## 回滾

```bash
git checkout v4.10.0
./tools/scripts/safe-redeploy.sh --all
# 然後手動 downgrade alembic（如果想清掉 v5.0 schema）
docker exec staffkm-agent alembic downgrade 0018_workflow_marketplace
```

v5.0 schema 是純 additive、不破壞 v4 code 路徑 — 即使不 downgrade 直接跑 v4
image 也能正常開（多出來的欄/表 v4 不知道、不會 query）。

## 後續

- v5.1 起會加 frontend region 感知（axios interceptor cache region 對應）
- 真實多 region 寫流量上線等 v5.x ops PR

問題 → 開 issue 標 `v5-upgrade`。
