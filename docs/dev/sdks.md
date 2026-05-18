# staffKM 官方 SDK

v4.5 Theme E 提供 3 個官方 SDK，覆蓋 staffKM 平台主要 API endpoint。

## 為什麼有 SDK

外部開發者整合 staffKM 時不必：

- 自己手讀 OpenAPI / curl 試 endpoint
- 自己處理 SSE chat streaming 的 framing
- 自己拼 X-API-Key / X-Workspace-ID header 邏輯

## OpenAPI spec

完整 spec 走平台內建 swagger：

- JSON: `http://localhost/api/openapi.json`
- Swagger UI: `http://localhost/api/docs`
- 生產：把 `localhost` 換成你的 base URL（例如 `https://staffkm.example.com`）

## Python — `staffkm-sdk`

```bash
pip install -e packages/python/staffkm-sdk
```

```python
from staffkm import StaffKM

with StaffKM(base_url="https://staffkm.example.com",
             api_key="sk_xxx",
             workspace_id="ws_abc") as client:
    for tok in client.chat.stream(application_id="app_123", message="hi"):
        print(tok, end="", flush=True)
```

> 舊版 `staffkm_sdk`（v0.1）仍然可 import，做為 backwards-compat 過渡用。

## TypeScript — `@staffkm/sdk`

```bash
npm install @staffkm/sdk
# 或 in monorepo
pnpm --filter @staffkm/sdk install
```

```typescript
import { StaffKM } from '@staffkm/sdk'

const client = new StaffKM({
  baseURL: 'https://staffkm.example.com',
  apiKey: 'sk_xxx',
  workspaceId: 'ws_abc',
})

await client.chat.stream('app_123', 'hi', {
  onToken: (t) => process.stdout.write(t),
})
```

## Go — `github.com/staffkm-platform/staffkm-sdk-go`

```bash
go get github.com/staffkm-platform/staffkm-sdk-go/staffkm
```

```go
client, _ := staffkm.New(staffkm.Options{
    BaseURL:     "https://staffkm.example.com",
    APIKey:      "sk_xxx",
    WorkspaceID: "ws_abc",
})
client.ChatStream("app_123", "hi", "", func(tok string) {
    fmt.Print(tok)
})
```

## 三個 SDK 共同覆蓋的 endpoint family

| 模組 | 端點 |
|---|---|
| `auth` | `POST /api/v1/auth/login`, `/refresh`, `GET /me` |
| `workspaces` | `GET /workspaces`, `POST /workspaces`, `GET /workspaces/{id}` |
| `knowledge` | `GET/POST /knowledge`, `POST /knowledge/{id}/documents`, `POST /knowledge/{id}/hit_test` |
| `applications` | `GET/POST /applications`, `GET /applications/{id}`, `POST /applications/{id}/run` |
| `chat` | `POST /applications/{id}/chat`（含 SSE 串流） |
| `quota` | `GET /quota/summary`, `PUT /quota`, `GET /admin/quota` |
| `billing` | `GET /billing/users`, `/users/{id}`, `/users.csv` |
| `plugins` | `GET /plugins`, `POST /plugins/reload` |

## 認證

- **API key**：在 admin → API Keys 申請；放 `X-API-Key` header
- **JWT token**：經 `auth.login` 取得 access_token；放 `Authorization: Bearer ...`
- **Workspace scope**：所有 SDK 都接受 `workspace_id` / `workspaceId` / `WorkspaceID`，轉成 `X-Workspace-ID` header

## 怎麼貢獻 SDK

1. 主架構在 `packages/python/staffkm-sdk/staffkm/`、`packages/ts/staffkm-sdk/`、`tools/sdk-go/`
2. 每個 resource 一檔；新增方法請對齊已存在的 pattern（短小、不過度抽象）
3. 新 endpoint 上 SDK 前先 curl 驗證 endpoint 真通（參考 CLAUDE.md routing 三層）
4. 加完跑語言對應驗證：
   - Python: `python -m py_compile staffkm/**/*.py`
   - TS: `pnpm --filter @staffkm/sdk typecheck`
   - Go: `go vet ./tools/sdk-go/...`
5. PR 加 example 到 `examples/`

## 不在 v4.5 範圍

- 不從 OpenAPI auto-codegen（v4.6 backlog 用 `openapi-generator`）
- 不 publish 到 PyPI / npm / pkg.go.dev（local install only）
- TS browser bundle（目前只測過 Node；fetch streaming 變體 v4.6 補）
- Python async resource 完整化（v4.6）
- Go context cancellation（v4.6）
