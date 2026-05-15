# GitHub Project 設定指南

> Sprint 0 第 1 項：建立 GitHub Project + Backlog 管理機制。本文件記錄完整設定步驟，新成員照做即可同步。

---

## 1. 建立 Project

```bash
# CLI 建立（GitHub Projects v2）
gh project create --owner <org-or-user> --title "staffKM v2"
```

或在網頁：`https://github.com/<owner>/projects/new` → 選 Board template。

---

## 2. 建立 Labels（一次匯入）

```bash
gh label create --file .github/labels.yml
```

或用 [ghaction-github-labeler](https://github.com/crazy-max/ghaction-github-labeler) 自動同步（已加入 CI workflow `.github/workflows/sync-labels.yml`）。

---

## 3. Project 欄位（Custom Fields）

進 Project 設定 → Fields，新增以下：

| 欄位名 | 類型 | 選項 |
|--------|------|------|
| **Status** | Single select | 📥 Backlog · 🎯 Ready · 🚧 In Progress · 👀 In Review · ✅ Done · 🔒 Blocked |
| **Phase** | Single select | P0 Kickoff · P1 Foundation · P2 Workflow · P3 ModelHub · P4 Advanced · P5 Launch |
| **Sprint** | Iteration | 雙週、從 W1 起算 |
| **Priority** | Single select | P0 Critical · P1 High · P2 Medium · P3 Low |
| **Role** | Single select | Architect · Backend · Frontend · DevOps · UX · Design · PMP |
| **Story Points** | Number | XS=1 · S=2 · M=3 · L=5 · XL=8 |
| **Milestone** | Single select | M1 · M2 · M3 · M4 · M5 |
| **Service** | Single select | gateway · auth · knowledge · agent · chat · web · infra |

---

## 4. Views（多視角）

建議建立以下 View：

### 4.1 📅 Sprint Board
- Layout: Board
- Group by: **Status**
- Filter: `iteration:@current`
- 用途：每日 standup、Sprint 進度

### 4.2 🗺️ Roadmap
- Layout: Roadmap
- Field: Sprint
- Group by: **Phase**
- 用途：跨 Phase 巨觀

### 4.3 👤 By Role
- Layout: Board
- Group by: **Role**
- Filter: `iteration:@current`
- 用途：各角色 workload 平衡

### 4.4 🎯 By Milestone
- Layout: Table
- Group by: **Milestone**
- Sort: Priority desc
- 用途：里程碑 health check

### 4.5 🔥 Backlog Triage
- Layout: Table
- Filter: `label:status:triage`
- Sort: Created asc
- 用途：每週分流（PMP 主持）

### 4.6 🚨 Risks & Blockers
- Layout: Board
- Filter: `label:status:blocked OR label:P0 OR label:security`
- 用途：每日 PMP 巡檢

---

## 5. Automation（GitHub Actions）

| 觸發 | 動作 |
|------|------|
| Issue 開啟 | 自動加入 Project，Status = 📥 Backlog |
| Issue 加 `status:in-progress` 標籤 | Status = 🚧 In Progress |
| PR 開啟並 link issue | Status = 👀 In Review |
| Issue 關閉 | Status = ✅ Done |
| PR merge to main | 觸發 changelog 更新 |
| 7 天無動 | 自動 stale + 通知 owner |

設定見 `.github/workflows/project-automation.yml`。

---

## 6. Issue 流程

```
建 issue（用 template）
   │
   ├─ 自動加 type:* + status:triage label
   ├─ 自動加入 Project board
   │
   ▼
PMP 每週 triage 會議
   │
   ├─ 評估 RICE 分數
   ├─ 補上 Phase / Sprint / Priority / Role / Story Points
   ├─ 從 status:triage 移到 status:ready
   │
   ▼
Sprint Planning（雙週四）
   │
   ├─ 從 ready pool 撈進當前 sprint
   ├─ 分配 assignee
   │
   ▼
Daily Standup
   │
   ├─ 每人 yesterday/today/blockers
   ├─ blocker 立即升級
   │
   ▼
PR 開啟 → Review → Merge → Issue auto close
```

---

## 7. Sprint 命名與長度

- **長度**：2 週
- **命名**：`Sprint W{week_start}-W{week_end}`，例如 `Sprint W1-W2`、`Sprint W3-W4`
- **里程碑日**：M1=W3、M2=W8、M3=W11、M4=W16、M5=W22

---

## 8. RACI（誰負責什麼）

| 活動 | R (Responsible) | A (Accountable) | C (Consulted) | I (Informed) |
|------|----------------|----------------|---------------|--------------|
| Backlog grooming | PMP | PMP | 全角色 leads | 全團隊 |
| RFC review | 提案者 | 架構師 | 全角色 leads | 全團隊 |
| Sprint planning | 全角色 | PMP | — | stakeholder |
| Sprint review/demo | 全角色 | PMP | stakeholder | 全公司 |
| Incident response | on-call | 架構師 | 涉及服務 lead | 全團隊 |
| Risk register update | PMP | 架構師 | 全角色 | stakeholder |

---

## 9. 第一次 Backlog 建立（本週）

執行：

```bash
# 把 33 個 backlog item 自動開成 issue
./tools/scripts/seed-backlog.sh
```

對應檔案 `tools/scripts/seed-backlog.sh` 會用 `gh issue create` 批次建立。
