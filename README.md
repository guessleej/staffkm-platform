# StaffKM Service — 行政人員知識管理系統

> 基於 MaxKB 架構重新設計，採分層模組化微服務架構，全繁體中文介面。

## 系統架構

```
┌─────────────────────────────────────────────────────────┐
│                      Nginx 反向代理                       │
│            前端靜態 (Vue 3)  +  /api → Gateway           │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│                   API Gateway (FastAPI :8000)             │
│  JWT 驗證 · 速率限制 · 結構化日誌 · Prometheus 監控      │
└──┬──────────┬──────────┬──────────┬──────────┬──────────┘
   │          │          │          │          │
   ▼          ▼          ▼          ▼          ▼
:8001      :8002      :8003      :8004      :8005
Knowledge  Agent      Auth     Integration  Chat
Service    Service   Service    Service    Service
(知識庫)  (AI代理人) (驗證)   (LINE/Teams) (對話)
   │          │          │          │          │
   └──────────┴──────────┴──────────┴──────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
    PostgreSQL+         Redis           MinIO
    pgvector         (快取/Session)   (文件儲存)
   (核心交易資料)                    (影像/日誌)
```

## 六大行政場景代理人

| 場景 ID | 代理人名稱 | 說明 |
|---|---|---|
| `official_doc` | 公文流程諮詢助理 | 公文撰寫、簽核流程、發文規定 |
| `hr_leave` | 人事差勤查詢助理 | 假別規定、差勤計算、出差補助 |
| `procurement` | 採購流程諮詢助理 | 政府採購法、招標流程、議價規定 |
| `budget` | 經費報支流程助理 | 差旅費、憑證要求、預算科目 |
| `sop` | 行政 SOP 查詢助理 | 各類行政標準作業程序 |
| `onboarding` | 新進人員訓練助理 | 到職流程、員工福利、常見問題 |

## 快速啟動

```bash
# 1. 複製環境設定
cp .env.example .env
# 填寫 OPENAI_API_KEY、SECRET_KEY 等必要設定

# 2. 啟動所有服務
docker compose up -d

# 3. 瀏覽系統
open http://localhost
# 預設帳號: admin / Admin@2026
```

## 技術規格

| 層次 | 技術選型 |
|---|---|
| API Gateway | FastAPI + Uvicorn |
| 微服務 | FastAPI (各服務獨立部署) |
| 向量資料庫 | PostgreSQL + pgvector |
| 物件儲存 | MinIO (文件/影像/日誌分離) |
| 快取/Session | Redis |
| 前端 | Vue 3 + TypeScript + Tailwind CSS |
| 容器化 | Docker Compose |
| 身分驗證 | JWT + LDAP/AD (可選) |
| 外部整合 | LINE Bot SDK v3、Microsoft Bot Framework |
| LLM | OpenAI GPT-4o / Anthropic Claude |
| Embedding | text-embedding-3-small (可換) |

## 服務端口對照

| 服務 | 端口 | 說明 |
|---|---|---|
| Nginx | 80/443 | 對外入口 |
| API Gateway | 8000 | 統一 API 入口 |
| Knowledge Service | 8001 | 知識庫管理 |
| Agent Service | 8002 | AI 代理人 |
| Auth Service | 8003 | 身分驗證 |
| Integration Service | 8004 | LINE/Teams 整合 |
| Chat Service | 8005 | 對話管理 |
| PostgreSQL | 5432 | 資料庫 |
| Redis | 6379 | 快取 |
| MinIO API | 9000 | 物件儲存 |
| MinIO Console | 9001 | 管理介面 |
