# 寫一個 staffKM Plugin（v4.3 Theme C）

> 第三方擴充 workflow node / LLM provider / lifecycle hook 的指南。

## TL;DR

```bash
pip install staffkm-plugin-sdk
mkdir my-plugin && cd my-plugin
# 寫 plugin.py + manifest.yaml
git init && git remote add origin <your-repo> && git push -u origin main
# 使用者端：
git clone <your-repo> ./plugins/my-plugin
docker exec staffkm-agent pip install -r /app/plugins/my-plugin/requirements.txt
curl -XPOST http://localhost/api/v1/admin/plugins/reload -H "Authorization: Bearer <admin>"
```

## 架構

agent service lifespan 啟動時 scan `/app/plugins/`（可用 `STAFFKM_PLUGINS_DIR` env var 覆寫），每個子目錄當一個 plugin：

```
/app/plugins/
├── weather-node/
│   ├── manifest.yaml      ← PluginManifest
│   ├── plugin.py          ← entry module
│   └── requirements.txt
└── …
```

plugin 註冊進 in-process registry，admin 可走 `GET /api/v1/admin/plugins` 列出、`POST /reload` hot reload。

> **v4.3 還沒接 executor**：plugin node 已 load 但 workflow runtime 不會呼叫，`executor.py` 有 TODO 標 v4.4 整合。Provider / Hook 同理。本 PR 先把 SDK + loader + admin API 落穩。

## 三種 plugin

### 1. Node — custom workflow node

```python
from staffkm_plugin_sdk import BaseNode, PluginContext

class WeatherNode(BaseNode):
    node_type = "weather_lookup"  # 全平台唯一

    async def execute(self, config: dict, ctx: PluginContext, inputs: dict) -> dict:
        import httpx
        city = config.get("city", "Taipei")
        out = config.get("output_variable", "weather")
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"https://wttr.in/{city}?format=3")
        return {out: r.text.strip()}
```

`config` 是 node JSON 設定，`ctx` 給 workspace_id / user_id / session_factory，`inputs` 是上游 node 輸出。回 dict（同步）或 `AsyncIterator[dict]`（stream）。

### 2. Provider — custom LLM/media provider

```python
from staffkm_plugin_sdk import BaseProvider

class MyLLMProvider(BaseProvider):
    provider_type = "my-llm"

    async def chat(self, model: str, messages: list[dict], **kw) -> dict:
        return {"text": "hello"}
```

### 3. Hook — workflow lifecycle hook

```python
from staffkm_plugin_sdk import BaseHook, PluginContext

class AuditHook(BaseHook):
    hook_type = "after_node"
    priority = 50

    async def handle(self, event: dict, ctx: PluginContext) -> None:
        # event: { node_key, node_type, output, latency_ms, ... }
        ...
```

`hook_type` ∈ `before_run` / `after_run` / `before_node` / `after_node`。低 `priority` 先跑。

## manifest.yaml

| 欄位 | 必要 | 說明 |
|---|---|---|
| `name` | ✓ | 2–64 字，全平台唯一 |
| `version` | ✓ | `MAJOR.MINOR.PATCH` |
| `description` | | 一句話 |
| `author` | | 作者 / 組織 |
| `license` | | 預設 `MIT` |
| `nodes` | | `["module:ClassName", ...]` |
| `providers` | | 同上 |
| `hooks` | | 同上 |
| `requirements` | | pip-installable deps |
| `min_platform_version` | | 預設 `4.3.0` |
| `icon` | | marketplace 顯示 |
| `tags` | | 分類 tag |
| `homepage` / `repository` | | URL |

範例：
```yaml
name: weather-node
version: 0.1.0
description: 查天氣（範例）
nodes:
  - plugin:WeatherNode
requirements:
  - httpx>=0.27
min_platform_version: "4.3.0"
tags: [demo, weather]
```

## 10 分鐘 tutorial

```bash
# 1. 建 plugin
mkdir my-first-plugin && cd my-first-plugin
cat > manifest.yaml <<'EOF'
name: hello-node
version: 0.1.0
nodes: ["plugin:HelloNode"]
EOF
cat > plugin.py <<'EOF'
from staffkm_plugin_sdk import BaseNode

class HelloNode(BaseNode):
    node_type = "say_hello"
    async def execute(self, config, ctx, inputs):
        return {"greeting": f"hi {config.get('name', 'world')}"}
EOF

# 2. 部到 agent
mkdir -p $REPO_ROOT/plugins
cp -r . $REPO_ROOT/plugins/hello-node
./tools/scripts/safe-redeploy.sh agent

# 3. 確認 load 進去
curl -H "Authorization: Bearer $ADMIN_JWT" \
     http://localhost/api/v1/admin/plugins | jq '.data.items[].nodes'
# → ["say_hello"]
```

## 發佈到 marketplace

1. push 到公開 git repo
2. PR 改 `tools/plugin-marketplace/index.json` 加你的 entry
3. 我們 review → 標 `verified: true`

詳見 `tools/plugin-marketplace/README.md`。

## 已知限制 / Roadmap

| 限制 | 規劃 |
|---|---|
| 沒 sandbox | v4.4 subprocess / WASM 隔離 |
| Plugin node executor 沒真接 | v4.4 整合 `_exec_*` fallback |
| Hook 還沒 dispatch | v4.4 在 run / node 邊界 emit |
| 沒 auto-install from git | v4.4 admin UI + git pull |
| 沒簽章驗證 | v4.4 公鑰簽 |
