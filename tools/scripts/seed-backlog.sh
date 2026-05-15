#!/usr/bin/env bash
# 把 staffKM v2 的 33 個 backlog 項目自動建立為 GitHub issues
# 用法：./tools/scripts/seed-backlog.sh
# 前置：gh CLI 已登入、labels 已 sync（gh label create --file .github/labels.yml）

set -euo pipefail

REPO=${REPO:-$(gh repo view --json nameWithOwner -q .nameWithOwner)}
echo "📝 將在 $REPO 建立 backlog issues..."
read -p "確認？[y/N] " ok
[[ "$ok" == "y" ]] || exit 0

create_issue() {
    local title="$1" labels="$2" body="$3"
    gh issue create --repo "$REPO" --title "$title" --label "$labels" --body "$body"
}

# ─── Sprint 0 ───────────────────────────────────────
create_issue \
  "[Feat] 建立 GitHub Project + Backlog 管理機制" \
  "type:feature,phase:0-kickoff,role:pmp,P0" \
  "見 .github/PROJECT_SETUP.md"

create_issue \
  "[Feat] 凍結 v2 範圍 + RFC 模板 + Definition of Done" \
  "type:docs,phase:0-kickoff,role:architect,P0" \
  "見 docs/rfc/RFC-TEMPLATE.md, docs/governance/definition-of-done.md"

create_issue \
  "[Feat] 訂 SLO/KPI" \
  "type:docs,phase:0-kickoff,role:pmp,role:architect,P0" \
  "見 docs/governance/slo.md"

# ─── Phase 1 ─────────────────────────────────────────
create_issue \
  "[Feat] 多租戶 IAM 重構（workspace_id + RBAC + ABAC）" \
  "type:feature,phase:1-foundation,role:architect,role:backend,P1" \
  "RFC-001"

create_issue \
  "[Feat] Folder 階層系統（KB/App/Model 巢狀）" \
  "type:feature,phase:1-foundation,role:backend,role:frontend,P1" \
  ""

create_issue \
  "[Feat] Application 版本控制（snapshot/diff/rollback）" \
  "type:feature,phase:1-foundation,role:backend,role:frontend,P2" \
  ""

create_issue \
  "[Feat] 設計系統 v1（design tokens + 30 元件 + workflow node icons）" \
  "type:feature,phase:1-foundation,role:design,P1" \
  ""

create_issue \
  "[Feat] UX 研究交付（persona/journey/sitemap/Figma）" \
  "type:feature,phase:1-foundation,role:ux,P1" \
  ""

create_issue \
  "[Feat] 品牌升級（Logo/色彩/字型/語調 brand guideline）" \
  "type:feature,phase:1-foundation,role:design,P1" \
  ""

create_issue \
  "[Feat] Monorepo 結構重組（apps/services/packages/tools/infra）" \
  "type:tech-debt,phase:1-foundation,role:architect,role:devops,P1" \
  "RFC-003"

create_issue \
  "[Milestone] M1: 多租戶 + Folder + 設計系統 GA" \
  "type:feature,phase:1-foundation,role:pmp,P0" \
  "驗收：workspace 切換可用、folder 拖拉 OK、Storybook 上線"

# ─── Phase 2 ─────────────────────────────────────────
create_issue "[Feat] Workflow Engine v2（DAG + sub-workflow + scoped context）" \
  "type:feature,phase:2-workflow,role:architect,role:backend,P1" "RFC-002"
create_issue "[Feat] 補齊 35+ Workflow Nodes" \
  "type:feature,phase:2-workflow,role:backend,P1" "Epic：每節點開子 issue"
create_issue "[Feat] 5 種 Workflow Manager" \
  "type:feature,phase:2-workflow,role:backend,P2" ""
create_issue "[Feat] Sandbox 容器（gVisor）" \
  "type:feature,phase:2-workflow,role:architect,role:devops,P1" ""
create_issue "[Feat] LogicFlow 編輯器升級" \
  "type:feature,phase:2-workflow,role:frontend,role:ux,P1" ""
create_issue "[Milestone] M2: Workflow Engine v2 GA" \
  "type:feature,phase:2-workflow,role:pmp,P0" "驗收：35 節點 / 子流程 / E2E ≥ 80%"

# ─── Phase 3 ─────────────────────────────────────────
create_issue "[Feat] Provider 抽象介面" \
  "type:feature,phase:3-modelhub,role:architect,P1" ""
create_issue "[Feat] 接入 20+ Model Providers" \
  "type:feature,phase:3-modelhub,role:backend,P1" "Epic：每 provider 子 issue"
create_issue "[Feat] Token 計帳 + Quota + 統計儀表板" \
  "type:feature,phase:3-modelhub,role:backend,role:frontend,P1" ""
create_issue "[Milestone] M3: Model Hub GA" \
  "type:feature,phase:3-modelhub,role:pmp,P0" ""

# ─── Phase 4 ─────────────────────────────────────────
create_issue "[Feat] 多媒體節點（image-to-video / text-to-video / video-understand）" \
  "type:feature,phase:4-advanced,role:backend,role:frontend,P2" ""
create_issue "[Feat] Long-term Memory Store" \
  "type:feature,phase:4-advanced,role:architect,role:backend,P1" ""
create_issue "[Feat] Event Trigger 系統（cron/webhook/file-upload）" \
  "type:feature,phase:4-advanced,role:backend,P2" ""
create_issue "[Feat] MCP Hub" \
  "type:feature,phase:4-advanced,role:backend,P2" ""
create_issue "[Feat] 整合層（LINE/Slack/Teams/Email + OAuth）" \
  "type:feature,phase:4-advanced,role:backend,P2" ""
create_issue "[Milestone] M4: 進階能力 GA" \
  "type:feature,phase:4-advanced,role:pmp,P0" ""

# ─── Phase 5 ─────────────────────────────────────────
create_issue "[Feat] Nuxt 3 遷移（前端體驗強化）" \
  "type:feature,phase:5-launch,role:frontend,role:ux,P1" "RFC-004"
create_issue "[Feat] 可觀測性堆疊（Prometheus + Loki + Tempo + Grafana）" \
  "type:feature,phase:5-launch,role:devops,P1" ""
create_issue "[Feat] K8s Helm chart + Image scan + Backup/DR" \
  "type:feature,phase:5-launch,role:devops,P1" ""
create_issue "[Feat] SDK 自動產生（Python/JS/Go）+ CLI + OpenAPI" \
  "type:feature,phase:5-launch,role:backend,P2" ""
create_issue "[Feat] 文件站 + Demo 影片 + Marketing site + Email 模板" \
  "type:feature,phase:5-launch,role:design,role:ux,P2" ""
create_issue "[Feat] 壓測（k6）+ Security audit + 5 名外部 UAT" \
  "type:feature,phase:5-launch,role:devops,role:ux,P1" ""
create_issue "[Milestone] M5: GA Release v2.0.0" \
  "type:feature,phase:5-launch,role:pmp,P0" ""

echo ""
echo "✅ 33 個 backlog issue 建立完成。"
echo "👉 接著到 GitHub Project 設定 fields、views（見 .github/PROJECT_SETUP.md）"
