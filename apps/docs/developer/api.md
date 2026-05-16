# REST API

所有 endpoint 走 workspace-scoped 前綴：

```
/api/v1/workspace/{workspace_id}/...
```

驗證：`Authorization: Bearer <api-key>` （`/admin/api-keys` 產生）。

## 主要 endpoint

| 群組          | 路徑                                          | 說明                          |
| ------------- | --------------------------------------------- | ----------------------------- |
| 對話           | `POST /agents/applications/{id}/chat`         | SSE 串流 chat                 |
| Application   | `GET/POST /applications`                      | CRUD + version 控制           |
| Workflow      | `POST /applications/{id}/workflow`            | 存 / 取 workflow              |
| Knowledge     | `GET /knowledge` / `POST /knowledge/{kb}/search` | RAG 檢索                    |
| Tool / Skill / DataSource | `/tools` `/skills` `/data-sources` | CRUD                         |
| Model Provider Registry | `GET /model-providers/registry`     | 25+ provider metadata         |
| Media Provider Registry | `GET /media-providers/registry`     | 5+ image/TTS/STT             |
| Usage         | `GET /usage/summary` `GET /usage/logs`        | Token 計帳                    |
| Quota         | `GET/PUT /quota`                              | 月度上限                      |
| Memory        | `GET/POST /memories` `POST /memories/search`  | 長期記憶                      |
| Trigger       | `GET/POST /triggers`                          | cron / interval / webhook     |
| MCP Hub       | `GET/POST /mcp/servers`                       | MCP 註冊與呼叫                |
| Folder        | `GET/POST /folders`                           | entity 樹                     |

## OpenAPI Spec

從 docker compose 跑中的服務抓：

```bash
./tools/scripts/dump-openapi.sh
# 輸出到 docs/openapi/{gateway,agent,knowledge,auth,chat}.json
```

從 spec 產任何語言 client：

```bash
npx @openapitools/openapi-generator-cli generate \
  -i docs/openapi/agent.json -g typescript-axios -o tools/codegen/sdk-ts/agent
```

## 錯誤碼

| HTTP | 意義                              |
| ---- | --------------------------------- |
| 401  | 未驗證（缺 / 壞 Bearer token）    |
| 403  | RBAC 拒絕（role 不夠）            |
| 404  | resource 不存在 / 不在當前 workspace |
| 422  | 請求格式 / 欄位驗證失敗            |
| 429  | quota 超額                        |
| 5xx  | 後端錯誤；附 `detail`             |
