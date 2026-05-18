# Starter Pack — v4.1 A

5 個預設 application templates，新 trial workspace 開通後一鍵安裝。

| ID | 名稱 | 場景 |
|----|------|------|
| 01-hr-assistant | HR 助理 | 請假 / 報帳 / 新人 onboarding |
| 02-it-helpdesk | IT Helpdesk | VPN / 軟體 / 帳號故障排除 |
| 03-knowledge-qa | 知識庫 QA | 通用文件問答（含引用） |
| 04-meeting-notes | 會議紀要助理 | 逐字稿 → 行動項萃取 |
| 05-sales-knowledge | 銷售知識助理 | 產品 / 競品 / 報價 |

## 安裝

admin role 透過 UI（待 v4.2）或直接 API：

```bash
# 列出
curl -H "Authorization: Bearer $TOKEN" -H "X-Workspace-ID: $WS" \
     http://localhost/api/v1/admin/starter-pack

# 安裝某一個
curl -X POST -H "Authorization: Bearer $TOKEN" -H "X-Workspace-ID: $WS" \
     http://localhost/api/v1/admin/starter-pack/01-hr-assistant/install
```

## Schema

每個 JSON：
- `name` / `description` / `icon` / `type`
- `system_prompt` / `welcome_message` / `suggested_questions`
- `nodes[]`：`node_key` / `node_type` / `label` / `config`
- `edges[]`：`source_node_key` / `target_node_key`
- `sample_knowledge[]`：（保留欄位，目前空）

對應 agent service 的 `applications` + `workflow_nodes` + `workflow_edges` 表。
