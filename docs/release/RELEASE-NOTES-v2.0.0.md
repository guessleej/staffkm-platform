# Release Notes — staffKM v2.0.0 GA

> **Date**：2026-05-17
> **Tag**：`v2.0.0`
> **Status**：GA（首個 production-ready release）

---

## 一句話

**staffKM v2.0** — 對話為中心、地端 LLM 預設、多租戶 + RBAC、25+ Model Provider、30+ Workflow Node、完整 Observability，從 PoC 到 production 一站到位的內部 AI 知識管理平台。

---

## 為何升級

| 你想要              | v1 有嗎 | v2.0 有 |
| ------------------- | :-----: | :-----: |
| 多部門隔離 + RBAC   |    -    |    ✓    |
| 工作流程編輯器       |  partial|    ✓    |
| 25+ Model Provider |    -    |    ✓    |
| Token 計帳 + Quota |    -    |    ✓    |
| Sandbox 隔離       |    -    |    ✓    |
| 完整 Observability |    -    |    ✓    |
| Python SDK + CLI   |    -    |    ✓    |
| Helm chart         |    -    |    ✓    |
| Backup/DR runbook  |    -    |    ✓    |

---

## 安裝（5 分鐘）

```bash
git clone https://github.com/guessleej/staffkm-platform.git
cd staffkm-platform
cp .env.example .env  # 必改 SECRET_KEY / JWT_SECRET / STAFFKM_SECRETS_KEY
docker compose -f infra/docker-compose.yml up -d
./tools/scripts/wait-healthy.sh
./tools/scripts/demo_seed.py  # 灌示範資料
open http://localhost
```

K8s（prod）見 [安裝部署](https://docs.staffkm.dev/admin/installation)。

---

## 主要里程碑

| 里程碑 | 範圍                              |
| ------ | --------------------------------- |
| **M1** | 多租戶 + Folder + 設計系統 + i18n + brand |
| **M2** | Workflow Engine + 5 種 Manager + Sandbox |
| **M3** | 25+ Provider + Token 計帳 + Quota Dashboard |
| **M4** | Media / Memory / Trigger / MCP Hub 啟動 |
| **M5** | Observability + Helm + SDK/CLI + Docs + DR runbook |

105 個 PR、14 份 RFC。

---

## Breaking changes

無 — v1 URL 仍可用（LegacyURLBridge 自動重寫）。但 **建議 90 天內** 將外部 integration 切到 v2 URL 結構：

```diff
- POST /api/v1/applications/{id}/chat
+ POST /api/v1/workspace/{ws}/agents/applications/{id}/chat
```

Deprecation header 會持續在 v1 endpoint response 中提示。

---

## 已知限制（v2.0.0）

| 項目                          | 影響                  | 計畫           |
| ----------------------------- | --------------------- | -------------- |
| trigger_worker 單副本         | 多 replica 重複觸發    | v2.1（advisory lock） |
| MCP server SSRF allow-list    | 任意 URL 可填          | v2.1           |
| dark mode 全量視圖替換         | 部分 view 仍寫死 gray  | v2.0.x 漸進    |
| eslint / vitest 接入          | 目前 vue-tsc 強制      | v2.1           |
| Memory 向量檢索               | 目前只有全文檢索        | M4 中段        |
| Trigger dispatcher           | 目前只 queue，不執行    | M4 中段        |
| Nuxt 3 migration（RFC-004）   | 仍是 Vue 3 SPA         | v3.0           |

---

## 升級 / Rollback

```bash
# 升級
helm upgrade staffkm ./infra/helm/staffkm --set image.tag=2.0.0

# Rollback
helm rollback staffkm 0
```

DB schema 透過 `bootstrap_ddl` 自動補欄（idempotent，向下相容）。

---

## 鳴謝

- 105 PR、14 RFC 全由 Claude Code agent 與工程團隊協作完成
- design tokens / brand guideline / personas / RFC 流程在過程中逐步成形
- 對話為中心 UI 對標 claude.ai

---

## 連結

- [文件](https://docs.staffkm.dev)
- [GitHub](https://github.com/guessleej/staffkm-platform)
- [Issues](https://github.com/guessleej/staffkm-platform/issues)
- [v2.1 Roadmap](https://github.com/guessleej/staffkm-platform/milestone/2)（待開）
