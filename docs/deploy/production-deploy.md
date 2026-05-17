# Production Deploy Runbook

> v2.2 production overlay — Caddy auto-TLS + secret hardening + monitoring stack.
> 假設目標是單機 / 小集群部署。多機 HA 請看 helm chart（待 v2.3）。

## 前置

| 條件 | 要求 |
|---|---|
| OS | Linux x86_64（測過 Ubuntu 22.04 / Debian 12） |
| Docker | ≥ 24.0、Compose plugin v2 |
| RAM | 建議 ≥ 8 GB（含 monitoring）|
| Disk | ≥ 50 GB（postgres + minio + ollama models）|
| Public DNS | A record 指到此 server（auto-TLS 需要）|
| Port 80/443 | open（auto-TLS challenge 需要）|

## 一次性設定（init）

```bash
# 1. clone repo
git clone https://github.com/guessleej/staffkm-platform.git /opt/staffkm
cd /opt/staffkm

# 2. 複製 + 改 env
cp .env.production.example .env.production
# 用 openssl 產生 secrets
SECRET_KEY=$(openssl rand -hex 32) sed -i "s|___CHANGE_ME_openssl_rand_hex_32___|$SECRET_KEY|" .env.production
DB_PW=$(openssl rand -hex 16) sed -i "s|___CHANGE_ME_TO_LONG_RANDOM___|$DB_PW|" .env.production
# 編輯 PUBLIC_DOMAIN / ADMIN_EMAIL / GRAFANA_BASIC_AUTH_HASH
vi .env.production

# 3. Grafana basic-auth hash
docker run --rm caddy:2.8-alpine caddy hash-password --plaintext 'YourGrafanaPwd'
# 把結果貼到 .env.production 的 GRAFANA_BASIC_AUTH_HASH

# 4. 第一次起服務（會花 5-10 分鐘 build all images + Caddy 拿 LE 證書）
./tools/scripts/safe-redeploy.sh --prod --all

# 5. 確認
curl -I https://staffkm.example.com
# HTTP/2 200 (or 301/302 to login)
```

## 日常維運

### 升級程式碼（git pull + rebuild）
```bash
cd /opt/staffkm
git pull
./tools/scripts/safe-redeploy.sh --prod --all
```

### 升級單一服務
```bash
./tools/scripts/safe-redeploy.sh --prod ui agent
```

### 看 log
```bash
docker compose --env-file .env.production \
  -f infra/docker-compose.yml \
  -f infra/docker-compose.production.yml \
  --project-directory . logs -f --tail=200 agent
```

### 進 grafana
- URL：`https://staffkm.example.com/grafana/`
- 帳號：admin / `GRAFANA_ADMIN_PASSWORD`（first login Caddy basic-auth 用 GRAFANA_BASIC_AUTH_HASH 對應的明文）

### 進 prometheus（除錯用，內網限定）
```bash
docker exec staffkm-prometheus wget -qO- http://localhost:9090/api/v1/targets | jq
```

## Caddy / TLS

- 自動 Let's Encrypt — `caddy_data` volume 存證書
- 證書 90 天到期，Caddy 自動續訂
- 強制 HTTP/2 + 啟用 HTTP/3 (QUIC)
- 全套 security headers (HSTS / XFO / CSP)
- SSE endpoints (`/api/v1/chat/*` 等) 自動 `flush_interval=-1` 不 buffer

### 換 domain
1. 改 `.env.production` PUBLIC_DOMAIN
2. `docker compose ... up -d --force-recreate caddy`
3. Caddy 自動申請新證書（保留舊的 fallback）

## Secret 管理

| 等級 | 建議 |
|---|---|
| 小團隊 | `.env.production` 設 `chmod 600`、用 git-crypt / age 加密進 repo |
| 中型 | docker secrets（compose `secrets:`） |
| 企業 | Hashicorp Vault / AWS Secrets Manager（待整合）|

**絕不要** commit `.env.production`，只 commit `.env.production.example`。

## 監控與告警

- Prometheus 跑於 backend network，scrape 5 個 API service + 自己
- Grafana 預設 dashboard：`infra/monitoring/grafana/dashboards/staffkm-overview.json`
- alerts：`infra/monitoring/alerts.yml`（rule load，notification channel 自配）

## 備份

見 `docs/deploy/backup-restore.md`（v2.2-C）。簡言：
- PG → daily `pg_dump` 到 `postgres_backups` volume / NFS / S3
- MinIO → `mc mirror` 到外部 storage
- 兩者都有 cron example

## 災難恢復演練（DR drill）

至少每季一次：
1. 停一台 server（或砍掉 volumes）
2. 用最近備份 `restore-postgres.sh` + `restore-minio.sh`
3. 驗證 login + chat 可用、KB doc 計數匹配

## 常見問題

### Caddy 拿不到證書
- 確認 `dig +short staffkm.example.com` 回對 IP
- 確認 80/443 對外開（防火牆 / 雲端 SG）
- 看 `docker logs staffkm-caddy` — `error: ... DNS problem` 通常是 DNS 沒生效

### 502 Bad Gateway
- `docker compose ps` 看哪個服務 unhealthy
- 通常 rebuild 後 nginx upstream IP 沒重抓 — `safe-redeploy.sh` 已內建處理

### Prometheus targets `down`
- `docker exec staffkm-prometheus wget -qO- http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.health=="down")'`
- 服務 healthy 但 metrics down → 確認該 service main.py 有 `Instrumentator().instrument(app).expose(app)`
