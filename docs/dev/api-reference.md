# staffKM API Reference

> 開發者文件 — 如何用 REST API 跟 staffKM 互動。
> 對應 OpenAPI spec 自動產：`https://staffkm.example.com/api/docs`（Swagger UI）

## 認證

3 種方式：

| 方式 | header | 用途 |
|---|---|---|
| **JWT Bearer** | `Authorization: Bearer eyJ...` | 模擬 user，全功能 |
| **API Key** | `Authorization: Bearer sk_xxx` 或 `X-API-Key: sk_xxx` | per-App、權限受限於該 App |
| **無**（公開分享） | — | 僅 `is_public=true` 的 App，限定 `/api/v1/public/*` |

### 拿 JWT
```bash
curl -X POST https://staffkm.example.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin@2026"}'
# {"data":{"access_token":"...","refresh_token":"...","user":{...}}}
```

### 拿 API Key
在 staffKM UI：應用卡片 → 「API Key」icon → 「+ 建立」 → 複製 `sk_...`

### Refresh token
```bash
curl -X POST https://staffkm.example.com/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"..."}'
```

## 主要資源

### Applications
- `GET    /api/v1/applications` — 列表（page / page_size）
- `POST   /api/v1/applications` — 建立
- `GET    /api/v1/applications/{id}` — 詳情
- `PUT    /api/v1/applications/{id}` — 更新
- `DELETE /api/v1/applications/{id}` — 刪除（軟刪 status='deleted'）
- `POST   /api/v1/applications/{id}/chat` — 跟此 App 對話（SSE）
- `POST   /api/v1/applications/preview/chat` — 預覽對話（無持久化、template gallery 試用用）

### Knowledge Bases
- `GET    /api/v1/knowledge/bases` — 列表
- `POST   /api/v1/knowledge/bases` — 建立
- `POST   /api/v1/knowledge/bases/{id}/web-sync` — 單 URL 同步
- `POST   /api/v1/knowledge/bases/{id}/web-sync/batch` — 多 URL（最多 20）
- `POST   /api/v1/knowledge/bases/{id}/web-sync/sitemap` — sitemap.xml 解析

### Documents
- `POST   /api/v1/knowledge/documents/{kb_id}/upload` — 上傳檔
- `POST   /api/v1/knowledge/documents/{kb_id}/inline-write` — 純文字寫入（給 SDK / Workflow 用）
- `GET    /api/v1/knowledge/documents/doc/{doc_id}/download` — 下載原檔

### Chat
- `POST   /api/v1/chat/conversations` — 開新對話
- `GET    /api/v1/chat/conversations` — 列表
- `POST   /api/v1/chat/conversations/{id}/messages/stream` — 發訊息（SSE）

### Workspace 自訂模板
- `GET    /api/v1/app-templates` — 列出 workspace 模板
- `POST   /api/v1/app-templates` — 建立
- `PUT    /api/v1/app-templates/{id}` — 更新
- `DELETE /api/v1/app-templates/{id}` — 刪除

### MCP Servers
- `GET    /api/v1/mcp/servers` — 列表
- `POST   /api/v1/mcp/servers` — 註冊 server
- `POST   /api/v1/mcp/servers/{id}/refresh` — 重抓 tools
- `GET    /api/v1/mcp/servers/{id}/tools` — 看 cached tools

### Triggers (排程)
- `GET    /api/v1/triggers`
- `POST   /api/v1/triggers` — kind: interval / cron / webhook
- `GET    /api/v1/triggers/{id}/runs` — 看執行紀錄

### Memories (長期記憶)
- `GET    /api/v1/memories?scope=user|app|team`
- `POST   /api/v1/memories` — 新增
- `POST   /api/v1/memories/search` — 關鍵字搜尋

### Usage / Quota
- `GET    /api/v1/usage/summary` — 本月用量總覽
- `GET    /api/v1/usage/quota`
- `PUT    /api/v1/usage/quota` — admin only

### Projects
- `GET    /api/v1/projects`
- `POST   /api/v1/projects/{id}/resources` — attach kb/app
- `DELETE /api/v1/projects/{id}/resources/{kind}/{resource_id}`

### Public (沒登入)
- `GET    /api/v1/public/applications/{id}` — 拿公開 App 資訊
- `POST   /api/v1/public/applications/{id}/chat` — 公開對話（SSE）

## 回應格式（統一）

```json
{
  "success": true,
  "data": { ... },
  "message": "成功",
  "code": 0
}
```

錯誤：
```json
{
  "detail": "錯誤描述",
  "code": 400
}
```

或 PR #155 後 422：
```json
{
  "detail": [{"loc":[...], "msg":"...", "type":"..."}]
}
```

## SSE Streaming

`POST /api/v1/applications/{id}/chat` 用 Server-Sent Events：

```
event: token
data: 你

event: token
data: 好

event: citations
data: [{"doc_name":"...","content":"...","score":0.87},...]

event: done
data: [DONE]
```

JS 範例：
```js
const resp = await fetch('/api/v1/applications/X/chat', {
  method: 'POST',
  headers: { 'Authorization': 'Bearer ...', 'Content-Type': 'application/json' },
  body: JSON.stringify({ messages: [{ role: 'user', content: 'Hello' }] }),
})
const reader = resp.body.getReader()
const decoder = new TextDecoder()
while (true) {
  const { done, value } = await reader.read()
  if (done) break
  for (const line of decoder.decode(value).split('\n')) {
    if (line.startsWith('data:')) console.log(line.slice(5))
  }
}
```

Python SDK：
```python
from staffkm_sdk import Client
c = Client(host='https://staffkm.example.com', api_key='sk_...')
for chunk in c.app('app-id').stream('Hello'):
    print(chunk, end='', flush=True)
```

## Rate limit / Quota

- 預設無 IP rate limit（gateway 層待加 v2.x）
- 個別 workspace 可設月 token / cost cap（429 hard-limit）
- CAPTCHA 自動防暴力（連 3 次登入失敗）

## OpenAPI / Swagger

完整自動產文件：
- Swagger UI: `https://staffkm.example.com/api/docs`
- ReDoc:      `https://staffkm.example.com/api/redoc`
- JSON spec:  `https://staffkm.example.com/api/openapi.json`

可以匯入 Postman / Insomnia 一鍵測。

## SDK

| 語言 | 套件 |
|---|---|
| Python | `pip install staffkm-sdk` |
| TypeScript | 待 v2.6 |
| Go | community contrib welcome |

Python SDK 範例：
```python
from staffkm_sdk import Client

c = Client(host='https://your.staffkm', api_key='sk_xxx')

# 列 KB
for kb in c.kbs.list():
    print(kb.name)

# Inline write 一段內容進 KB
c.kbs.inline_write('kb-id', content='...', title='...')

# 跟 App 對話
resp = c.app('app-id').chat('你好')
print(resp.content)
print(resp.citations)
```

## Webhook（被 staffKM 主動 call）

留給：
- LINE webhook: `POST /api/v1/integrations/line/webhook`
- Teams webhook: `POST /api/v1/integrations/teams/webhook`

待整合（message handler 未完成）。

## 變更日誌

每個 endpoint 變更會記在 `CHANGELOG.md`。Breaking change 在 v3.0 之前不會發生（v1 endpoints 仍 LegacyURLBridge 自動 rewrite，Sunset header 標明 deprecation）。

## 問題

- GitHub Issues: https://github.com/guessleej/staffkm-platform/issues
- 私下：jefflee@cloudinfo.com.tw
