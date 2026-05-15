# ══════════════════════════════════════════════════════════════════
#  StaffKM — Docker Compose 操作指令集
#  使用方式：make <指令>
# ══════════════════════════════════════════════════════════════════

.PHONY: help up down dev build rebuild logs ps health backup restore clean \
        shell-gateway shell-db migrate seed monitoring

# 預設顯示說明
.DEFAULT_GOAL := help

# 顏色
CYAN  := \033[0;36m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED   := \033[0;31m
RESET := \033[0m

## ── 基本操作 ────────────────────────────────────────────────────

help: ## 顯示此說明文字
	@echo ""
	@echo "$(CYAN)StaffKM Docker 操作指令$(RESET)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""

up: ## 啟動所有服務（正式模式）
	@echo "$(CYAN)▶ 啟動 StaffKM 服務...$(RESET)"
	docker compose -f docker-compose.yml up -d
	@echo "$(GREEN)✅ 服務已啟動，請瀏覽 http://localhost$(RESET)"

dev: ## 啟動開發模式（熱重載，開放各服務端口）
	@echo "$(CYAN)▶ 啟動開發模式...$(RESET)"
	@[ -f .env ] || (cp .env.example .env && echo "$(YELLOW)⚠️  已建立 .env，請填寫必要設定$(RESET)")
	docker compose up -d
	@echo "$(GREEN)✅ 開發服務已啟動$(RESET)"
	@echo "  Gateway:    http://localhost:8000/api/docs"
	@echo "  Knowledge:  http://localhost:8001/docs"
	@echo "  Agent:      http://localhost:8002/docs"
	@echo "  Auth:       http://localhost:8003/docs"
	@echo "  MinIO:      http://localhost:9001"

down: ## 停止並移除所有容器
	@echo "$(CYAN)▶ 停止服務...$(RESET)"
	docker compose down

stop: ## 停止服務（保留容器）
	docker compose stop

## ── 建置 ────────────────────────────────────────────────────────

build: ## 建置所有映像
	@echo "$(CYAN)▶ 建置所有映像...$(RESET)"
	docker compose build --parallel

rebuild: ## 強制重新建置（不使用快取）
	@echo "$(CYAN)▶ 強制重新建置...$(RESET)"
	docker compose build --no-cache --parallel

build-ui: ## 只建置前端映像
	docker compose build ui

push: ## 推送所有映像到 Registry
	@[ -n "$(REGISTRY)" ] || (echo "$(RED)❌ 請指定 REGISTRY=your.registry.com$(RESET)" && exit 1)
	docker compose push

## ── 日誌與監控 ──────────────────────────────────────────────────

logs: ## 查看所有服務日誌（即時）
	docker compose logs -f --tail=100

logs-gateway: ## 查看 Gateway 日誌
	docker compose logs -f --tail=100 gateway

logs-knowledge: ## 查看 Knowledge Service 日誌
	docker compose logs -f --tail=100 knowledge knowledge-worker

logs-agent: ## 查看 Agent Service 日誌
	docker compose logs -f --tail=100 agent

logs-auth: ## 查看 Auth Service 日誌
	docker compose logs -f --tail=100 auth

logs-chat: ## 查看 Chat Service 日誌
	docker compose logs -f --tail=100 chat

ps: ## 查看所有容器狀態
	docker compose ps

health: ## 快速健康檢查所有服務
	@echo "$(CYAN)▶ 健康狀態檢查$(RESET)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@for svc in gateway knowledge agent auth chat; do \
		port=$$(docker compose port $$svc $$(case $$svc in gateway) echo 8000;; knowledge) echo 8001;; agent) echo 8002;; auth) echo 8003;; chat) echo 8005;; esac) 2>/dev/null | cut -d: -f2); \
		if curl -sf http://localhost:$$port/health > /dev/null 2>&1; then \
			echo "  $(GREEN)✅ $$svc$(RESET)"; \
		else \
			echo "  $(RED)❌ $$svc$(RESET)"; \
		fi; \
	done

monitoring: ## 啟動監控服務（Prometheus + Grafana）
	docker compose --profile monitoring up -d prometheus grafana
	@echo "$(GREEN)✅ Grafana: http://localhost:3000$(RESET)"

## ── 資料庫操作 ──────────────────────────────────────────────────

migrate: ## 執行資料庫 Migration
	@echo "$(CYAN)▶ 執行 Migration...$(RESET)"
	docker compose run --rm db-migrate

shell-db: ## 進入 PostgreSQL 互動介面
	docker compose exec postgres psql -U $${DB_USER:-staffkm} -d $${DB_NAME:-staffkm}

backup: ## 備份資料庫至 ./backups/
	@mkdir -p backups
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	docker compose exec -T postgres pg_dump \
		-U $${DB_USER:-staffkm} $${DB_NAME:-staffkm} \
		| gzip > backups/staffkm_$$TIMESTAMP.sql.gz; \
	echo "$(GREEN)✅ 備份完成：backups/staffkm_$$TIMESTAMP.sql.gz$(RESET)"

restore: ## 從備份還原資料庫（FILE=backups/xxx.sql.gz）
	@[ -n "$(FILE)" ] || (echo "$(RED)❌ 請指定 FILE=backups/xxx.sql.gz$(RESET)" && exit 1)
	@echo "$(YELLOW)⚠️  這將覆蓋現有資料，請確認後按 Enter$(RESET)"; read confirm
	gunzip -c $(FILE) | docker compose exec -T postgres psql \
		-U $${DB_USER:-staffkm} -d $${DB_NAME:-staffkm}
	@echo "$(GREEN)✅ 資料庫還原完成$(RESET)"

## ── 進入容器 Shell ───────────────────────────────────────────────

shell-gateway: ## 進入 Gateway 容器
	docker compose exec gateway sh

shell-knowledge: ## 進入 Knowledge Service 容器
	docker compose exec knowledge sh

shell-agent: ## 進入 Agent Service 容器
	docker compose exec agent sh

## ── 維護 ────────────────────────────────────────────────────────

clean: ## 停止服務並清除 Volume（⚠️ 資料將被刪除）
	@echo "$(RED)⚠️  這將刪除所有容器和資料，請確認後按 Enter$(RESET)"; read confirm
	docker compose down -v --remove-orphans
	@echo "$(GREEN)✅ 清除完成$(RESET)"

prune: ## 清除未使用的 Docker 映像
	docker image prune -f
	docker builder prune -f

env-check: ## 驗證 .env 必要設定
	@echo "$(CYAN)▶ 檢查環境設定...$(RESET)"
	@[ -f .env ] || (echo "$(RED)❌ 找不到 .env，請執行 cp .env.example .env$(RESET)" && exit 1)
	@grep -q "^OPENAI_API_KEY=sk-" .env \
		&& echo "  $(GREEN)✅ OPENAI_API_KEY$(RESET)" \
		|| echo "  $(RED)❌ OPENAI_API_KEY 未設定$(RESET)"
	@grep -q "^SECRET_KEY=" .env && grep -v "changeme" .env | grep -q "^SECRET_KEY=" \
		&& echo "  $(GREEN)✅ SECRET_KEY$(RESET)" \
		|| echo "  $(YELLOW)⚠️  SECRET_KEY 使用預設值（請更換）$(RESET)"
	@grep -q "^DB_PASSWORD=" .env \
		&& echo "  $(GREEN)✅ DB_PASSWORD$(RESET)" \
		|| echo "  $(RED)❌ DB_PASSWORD 未設定$(RESET)"
