# staffkm-cli — admin / DevOps CLI

> v4.4 Theme D 起，CLI 涵蓋平台 80% admin 操作。

## 安裝

```bash
cd apps/admin-cli
pip install -e .
# 或 (monorepo uv 環境)
uv pip install -e apps/admin-cli
```

驗證：

```bash
staffkm-cli --help
# 等效 alias
staffkm --help
```

## 兩種認證模式

CLI 同時支援兩種 auth：

| 模式 | 適用 | 設定 |
|---|---|---|
| **env-based (legacy)** | `ping` / `apps` / `chat` / `usage` / `quota` | `STAFFKM_BASE_URL` / `STAFFKM_API_KEY` / `STAFFKM_WORKSPACE_ID` 或 `--base-url --api-key --workspace` |
| **cred file (v4.4 D)** | `login` / `workspace` / `app` / `kb` / `user` / `plugin` / `observability` / `billing` | `~/.staffkm/credentials.json`（`login` 自動寫入） |

兩者可並存：env-based 適合 CI 用 API key；cred file 適合人類 dev 機。

## Login flow

```bash
staffkm-cli login --base http://localhost --email admin@example.com
# 提示密碼 → POST /api/v1/auth/login → 拿 JWT → 存 ~/.staffkm/credentials.json (0600)
```

`credentials.json` 結構：

```json
{
  "base": "http://localhost",
  "token": "eyJhbGciOi...",
  "workspace_id": "11111111-2222-3333-4444-555555555555"
}
```

切換 workspace：

```bash
staffkm-cli workspace list
staffkm-cli workspace switch <workspace-id>
```

登出：

```bash
staffkm-cli logout
```

## Command groups 速查

```bash
# workspace
staffkm-cli workspace list
staffkm-cli workspace create "My team"
staffkm-cli workspace delete <id>
staffkm-cli workspace switch <id>

# app
staffkm-cli app list
staffkm-cli app install starter-pack rag-basic
staffkm-cli app export <app-id> > app.json
staffkm-cli app import app.json

# kb
staffkm-cli kb list
staffkm-cli kb create "Policies"
staffkm-cli kb upload <kb-id> ./handbook.pdf
staffkm-cli kb search <kb-id> "leave policy" --top-k 5

# user
staffkm-cli user list
staffkm-cli user invite teammate@example.com --role member
staffkm-cli user quota set <user-id> --tokens 100000 --cost 5.0

# plugin (v4.3 Theme C)
staffkm-cli plugin list
staffkm-cli plugin reload

# observability
staffkm-cli observability slow-queries --limit 50
staffkm-cli observability heartbeats
staffkm-cli observability webhook-outbox --state failed

# billing
staffkm-cli billing report --month 2026-05
staffkm-cli billing report --month 2026-05 --csv > may.csv
```

## Shell completion

Click 自帶 completion，不用打包額外 script：

```bash
# zsh
eval "$(_STAFFKM_CLI_COMPLETE=zsh_source staffkm-cli)"

# bash
eval "$(_STAFFKM_CLI_COMPLETE=bash_source staffkm-cli)"

# fish
_STAFFKM_CLI_COMPLETE=fish_source staffkm-cli | source
```

寫進 `~/.zshrc` / `~/.bashrc` 持久化。

## 排錯

| 症狀 | 解 |
|---|---|
| `not logged in. Run: staffkm-cli login` | 跑 `login`，確認 `~/.staffkm/credentials.json` 存在 |
| `401 Unauthorized` | token 過期，重新 `login` |
| 連不到 host | 確認 `--base` URL 正確、gateway 起來 |
| `no access_token in response` | 後端登入回應格式變了；對齊 `services/auth/app/api/login.py` 回傳 schema |

## 不在範圍 / Roadmap

- PyPI / Homebrew package — v4.5
- Shell completion 自動安裝 script — v4.5
- Sub-command plugin 自動發現（讓 staffkm-cli plugin 自定義 sub-command）— v4.5
- 互動式 TUI（rich.prompt 以外）— 不排
