# 多租戶與 RBAC

## 模型

- **workspace**：第一層；資料完全隔離。
- **member**：使用者與 workspace 的多對多關係，附帶 role。
- **role**：owner / admin / editor / viewer（依序遞減）。

## 三層隔離

1. **Path**：URL 必須帶 `workspace_id`（`/api/v1/workspace/{ws}/...`）
2. **RBAC**：`require_member` / `require_writer` / `require_admin` / `require_owner`
3. **SQL**：所有 query 過 `WorkspaceScopedQuery`，自動加 `WHERE workspace_id = :ws`

## 角色權限矩陣

| 動作                  | viewer | editor | admin | owner |
| --------------------- | :----: | :----: | :---: | :---: |
| 對話 / 看 KB           |   ✓    |   ✓    |   ✓   |   ✓   |
| 建 application        |        |   ✓    |   ✓   |   ✓   |
| 改 model provider     |        |        |   ✓   |   ✓   |
| 設 quota              |        |        |   ✓   |   ✓   |
| 邀請 admin            |        |        |       |   ✓   |
| 刪 workspace          |        |        |       |   ✓   |

## 邀請使用者

`/admin/users` → 新增 → 填 email + 選 role。
- SSO：使用者首次登入自動建立帳號；admin 之後改 role
- 本地：admin 設定初始密碼，使用者首次登入強制改

## Workspace 切換

UI 右上下拉；CLI 用 `--workspace` 旗標或 `STAFFKM_WORKSPACE_ID` 環境變數。
