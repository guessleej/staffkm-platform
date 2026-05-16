# Backup / Disaster Recovery Runbook v1.0

> M5 GA。當 prod 出事時，**先穩住、再復原**。
> 目標：**RPO ≤ 15 min**、**RTO ≤ 1 hour**（managed Postgres pre-condition）。

## 1. 備份策略

| 資料            | 方式                             | 週期           | 保存          | 驗證            |
| --------------- | -------------------------------- | -------------- | ------------- | --------------- |
| Postgres        | managed snapshot（AWS RDS / GCP CloudSQL）| 連續 + 每日 | 35 天 + 月歸檔 | 每月 restore drill |
| pgvector index  | 隨 Postgres 一起                 | -              | -             | 由 application bootstrap_ddl 重建 |
| Embeddings 原文 | 物件儲存（S3 / GCS）              | 上傳即備       | 永久          | 季度 list audit |
| 設定 secrets    | KMS + git-crypt（敏感檔離庫）     | 變更即同步      | 永久          | 季度 key rotation |
| 應用 deployment | Helm chart in Git                | 每次 release   | git history    | 每個 release tag |

## 2. 還原情境

### 2.1 單表壞掉（人為 DELETE / drop）

1. `kubectl scale deploy --all --replicas=0`（停止寫入）
2. AWS Console / `gcloud sql instances clone` → 新 instance 從 5 分鐘前的 snapshot
3. 從新 instance dump 出該表 → 還原到 prod
4. `kubectl scale --replicas=...`
5. **必做**：寫 incident note `docs/ops/incidents/YYYY-MM-DD-{slug}.md`

### 2.2 整個資料庫 corrupted

1. Helm `--set postgres.externalUrl=<new-restored-url>` upgrade
2. 應用會自動跑 bootstrap_ddl 補缺失欄位（idempotent）
3. 監控 5xx 5 分鐘，無事即解除維護模式

### 2.3 區域性 outage（雲商整個 region 掛）

1. failover：DNS 切到 DR region（事前已有 read replica）
2. promote replica：`aws rds promote-read-replica`
3. Helm install 到 DR k8s cluster；指向 promoted DB
4. RTO 目標 < 1 hour

## 3. 還原演練（每月一次）

```bash
# 1. 建立隔離測試環境
helm install staffkm-drtest ./infra/helm/staffkm \
  --namespace dr-test --create-namespace \
  --set postgres.externalUrl=<snapshot-restored-url>

# 2. 跑健康檢查
./tools/scripts/wait-healthy.sh

# 3. 跑 E2E
cd tools/e2e && pnpm test

# 4. 紀錄到 docs/ops/dr-drills/YYYY-MM-DD.md
```

## 4. Secrets / Key rotation

### Fernet 主金鑰
1. 產新 key：`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
2. 暫時設兩把（程式內 `MultiFernet` — M5 中段補）
3. 跑遷移腳本：`tools/scripts/rotate_secrets.py`（M5 中段補）— 解舊密 → 寫新密
4. 移除舊 key

### JWT 簽章 / OIDC
- 30 天一次
- `kubectl rollout restart deploy --all`（讓服務重新載入）

## 5. 監控告警 → 動作對應

| Alert           | 第一動作                       | 升級條件                |
| --------------- | ------------------------------ | ----------------------- |
| ServiceDown 2m  | check pod / restart           | 5m 仍 down → page on-call |
| 5xx > 5% 5m     | logs + recent deploy diff      | rollback                |
| QuotaBreach     | 確認被攻擊 / quota 太緊；先放行 | 持續 30m → 自動加 cap   |
| WorkerStalled   | restart trigger worker pod     | 兩次 / 24h → 寫 incident |
| PgVectorSlow    | 看 RDS metrics / index 健康    | 持續 → 跑 ANALYZE       |

## 6. Post-mortem 模板

每次 P1 / P2 incident 24h 內寫 `docs/ops/incidents/`：

```md
## 摘要
**發生**：2026-05-16 14:32 ~ 14:48 (16 min)
**影響**：~200 使用者看到 5xx；3 個 workspace 寫入失敗

## 時間軸（UTC+8）
14:32 alert 觸發 ServiceDown gateway
14:35 on-call 接手
14:42 找到 root cause — Postgres connection pool 滿
14:48 重啟 + 加 pool size → 解決

## Root cause
- 某 workflow 沒有 await session.close → connection leak

## 解法
- 立即：重啟、加 pool size 50 → 100
- 短期：修 leak（PR #...）
- 長期：加 connection lifetime alert

## 教訓 / Action items
- [ ] 加 connection lifetime > 5min 告警
- [ ] 在 base_agent 加 context manager 強制 close
- [ ] 此類 alert 升級為 page（不僅 warning）
```
