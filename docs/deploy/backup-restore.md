# Backup & Restore Runbook

> v2.2-C — staffKM 生產資料的備份 / 還原 / DR drill SOP。
> 兩個 datastore：**PostgreSQL**（all metadata + vectors）+ **MinIO**（文件原檔）。

## TL;DR

```bash
# 1. 一次性：安裝 cron
sudo crontab -e
# 貼 tools/backup/crontab.example 內容

# 2. 確認備份目錄存在 & 容器可寫
sudo mkdir -p /var/lib/staffkm/backups/{postgres,minio}
sudo chown -R 999:999 /var/lib/staffkm/backups   # postgres uid

# 3. 立刻跑一次驗證
./tools/backup/backup-postgres.sh
./tools/backup/backup-minio.sh
ls -lh /var/lib/staffkm/backups/postgres
```

## 備份策略

| Datastore | 工具 | 頻率 | 保留 | 容量估算 |
|---|---|---|---|---|
| PostgreSQL | `pg_dump --format=custom -Z 9` | daily 02:00 | 14 daily + 8 weekly | ~5 MB / 100 用戶 / 月 |
| MinIO | `mc mirror` | daily 02:15 | 14 份 | 等比原檔大小 × 14 |
| Ollama models | 不備（重抓即可） | n/a | n/a | n/a |
| Redis | 不備（cache） | n/a | n/a | n/a |

### 為什麼這樣設計

- **PG `--format=custom -Z 9`**：高壓縮、支援平行還原、可選擇性 restore 單一 table
- **PG 保留 14 daily + 8 weekly**：日常 rollback 用 daily；季度資料對帳用 weekly
- **MinIO `mc mirror --remove`**：完整 snapshot，restore 時 1-to-1 對齊
- **不備 Ollama**：重新 `ollama pull` 就行，幾 GB 模型不值得備

## 異地存放（強烈建議）

兩個 script 都支援 `BACKUP_S3_URL` env：

```bash
# 在 .env.production 加
BACKUP_S3_URL=https://AWS_KEY:AWS_SECRET@s3.amazonaws.com/your-bucket
# 或 minio.example.com 的 S3-compat endpoint
```

設了之後 script 跑完 local backup 會自動 `mc cp` 推一份到 S3。

## 還原流程

### 場景 A：誤刪一個 KB（要回到昨天）

```bash
# 1. 找昨天的 dump
ls -1t /var/lib/staffkm/backups/postgres/ | head -3
# staffkm-20260516-0200.dump

# 2. 互動式還原（會 DROP + recreate db）
./tools/backup/restore-postgres.sh staffkm-20260516-0200.dump

# 3. 重啟所有 backend（清 connection cache）
./tools/scripts/safe-redeploy.sh --prod knowledge agent
```

### 場景 B：整台 server 重灌

```bash
# 1. 把備份 dump + minio snapshot 從 S3 拉回
mkdir -p /var/lib/staffkm/backups/{postgres,minio}
aws s3 sync s3://your-bucket/ /var/lib/staffkm/backups/  # 或 mc cp

# 2. clone repo + 還原 .env.production
git clone https://github.com/guessleej/staffkm-platform.git /opt/staffkm
cd /opt/staffkm
# 把備份的 .env.production 拷回來（這個檔 .gitignore 排除，要外部管理）

# 3. 啟動底層（不啟動 app — 先還原資料才啟動）
docker compose --env-file .env.production \
  -f infra/docker-compose.yml \
  -f infra/docker-compose.production.yml \
  --project-directory . \
  up -d postgres redis minio

# 4. 等 postgres / minio healthy
sleep 30

# 5. 還原 PG
./tools/backup/restore-postgres.sh   # 互動選最新 dump

# 6. 還原 MinIO
./tools/backup/restore-minio.sh

# 7. 啟動全部
./tools/scripts/safe-redeploy.sh --prod --all
```

### 場景 C：只想匯出一個 table 看

```bash
# pg_restore 支援 --table 選擇性 restore
docker exec staffkm-postgres pg_restore \
  -U staffkm -d staffkm_temp \
  --table=applications \
  /backups/staffkm-20260517-0200.dump
```

## 災難恢復演練（DR drill）— 每季

**目標**：能在 1 小時內從零還原到可用狀態，data loss ≤ 24h。

### 演練步驟

1. **準備 staging server**（或本機 docker-in-docker）
2. **故意砍掉 staging volumes**：
   ```bash
   docker compose -f ... down -v
   ```
3. **照「場景 B」流程跑** — 計時開始
4. **驗證**：
   - login 可用
   - 任一 KB 文件計數匹配備份前
   - chat 跑得起來 + citation 正確
5. **記錄**：完整時間 / 卡點 / 改進項目
6. **歸檔到** `docs/deploy/dr-drills/YYYY-Q[1-4].md`

### 演練 checklist

- [ ] backup dump 拿得到（local + S3）
- [ ] `.env.production` 拿得到（要外部 secret 管理）
- [ ] DNS 切到新 server
- [ ] Caddy 拿到新證書（or 把舊 caddy_data 還原）
- [ ] Ollama model 重抓
- [ ] 第一個 user login 成功
- [ ] 第一筆 chat 完整工作（含 RAG）

## Monitoring

### 失敗告警

`crontab.example` 內建一個 hourly check：
- `/var/lib/staffkm/backups/{postgres,minio}/.last-backup-success` 超過 26 小時沒更新 → 寫 ALERT log

進階：把 ALERT 轉接 PagerDuty / Slack webhook（自配）。

### 容量警示

`du -sh /var/lib/staffkm/backups/` 應該穩定（保留策略生效）。如果無上限成長，檢查 prune section 是否錯誤。

## 注意事項

| 注意 | 為什麼 |
|---|---|
| `.env.production` 不要備到 git 內 | secret leak |
| MinIO restore 用 `--overwrite` 但**不**用 `--remove` | 避免誤刪比快照新的 key |
| restore PG 之前**一定要**停 agent / knowledge | 防 live connection 卡 DROP DATABASE |
| 演練至少**季度一次** | 沒練過的 backup 等於沒備 |
