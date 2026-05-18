# staffkm-plugin-sdk

staffKM 平台 v4.3 Plugin SDK — 第三方寫 custom **node / provider / hook**。

## 安裝

```bash
pip install staffkm-plugin-sdk
```

monorepo 內走 editable install：
```bash
pip install -e packages/python/staffkm-plugin-sdk
```

## 三種 plugin

```python
from staffkm_plugin_sdk import BaseNode, BaseProvider, BaseHook, PluginContext

class WeatherNode(BaseNode):
    node_type = "weather_lookup"
    async def execute(self, config, ctx, inputs):
        return {"weather": "sunny"}
```

## manifest.yaml

```yaml
name: my-plugin
version: 0.1.0
nodes: ["plugin:WeatherNode"]
requirements: ["httpx>=0.27"]
min_platform_version: "4.3.0"
```

## 範例

見 `examples/weather_node/`。

完整文件：`docs/dev/plugins.md`。
