# 安裝部署

## Docker Compose（dev / POC）

```bash
git clone https://github.com/guessleej/staffkm-platform.git
cd staffkm-platform
cp .env.example .env       # 編輯 secrets（最少改 SECRET_KEY / JWT_SECRET）
docker compose -f infra/docker-compose.yml up -d
./tools/scripts/wait-healthy.sh
```

- UI：`http://localhost`
- 預設帳號：見 `.env`（首次啟動會 seed 一個 admin）

## Kubernetes（prod）

```bash
# 1. 準備 Postgres（建議 managed RDS / CloudSQL）
# 2. 建 namespace + 必要 secret
kubectl create ns staffkm
kubectl create secret generic staffkm-secrets-key \
  --from-literal=key="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"

# 3. install
helm upgrade --install staffkm ./infra/helm/staffkm \
  --namespace staffkm \
  --set postgres.externalUrl="postgresql://user:pw@db.example.com:5432/staffkm" \
  --set ingress.host="staffkm.example.com" \
  --set image.tag="2.0.0"
```

升級：

```bash
helm upgrade staffkm ./infra/helm/staffkm --reuse-values --set image.tag="2.0.1"
```

## 環境變數速查

| 變數                    | 必填    | 說明                                |
| ----------------------- | ------- | ----------------------------------- |
| SECRET_KEY              | ✓       | gateway / session                   |
| JWT_SECRET              | ✓       | JWT 簽章                            |
| STAFFKM_SECRETS_KEY     | ✓       | Fernet 主金鑰（API key 加密）       |
| DB_URL                  | ✓       | `postgresql+asyncpg://...`          |
| OPENAI_API_KEY          | optional | 全域 fallback                       |
| OPENAI_MODEL            | optional | 預設模型                            |
| KNOWLEDGE_SERVICE_URL   | optional | 跨服務呼叫；compose 內已 wire       |

## 升級檢查清單

- [ ] 跑 `tools/scripts/dump-openapi.sh` 對比 API 變更
- [ ] 確認 Helm values 沒有 breaking 預設值
- [ ] backup DB 一份（snapshot 即可）
- [ ] 觀察新版本 5xx / latency 30 分鐘
