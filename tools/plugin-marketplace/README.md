# staffKM Plugin Marketplace

> v4.3 Theme C — 第三方 plugin 公開索引。

## 想 publish 你的 plugin？

1. 用 `staffkm-plugin-sdk` 寫一個 plugin（範例見 `packages/python/staffkm-plugin-sdk/examples/weather_node/`）。
2. 結構：
   ```
   my-plugin/
     manifest.yaml         # PluginManifest（必要）
     plugin.py             # entry module
     requirements.txt      # pip deps
     README.md
   ```
3. push 到一個公開 git repo。
4. 對本 repo 開 PR 編輯 `index.json` 加進 `plugins[]`：
   ```json
   {
     "name": "my-plugin",
     "description": "做什麼的",
     "repository": "https://github.com/<you>/<repo>",
     "min_platform_version": "4.3.0",
     "tags": ["category", "..."],
     "verified": false
   }
   ```
5. 我們 review 後標 `"verified": true`。

## 使用者怎麼裝

```bash
# 1. clone plugin 到 host 的 ./plugins/<name>/
git clone https://github.com/<you>/<repo> ./plugins/my-plugin

# 2. 裝 plugin 的 deps 到 agent container
docker exec staffkm-agent pip install -r /app/plugins/my-plugin/requirements.txt

# 3. hot reload
curl -X POST http://localhost/api/v1/admin/plugins/reload \
  -H "Authorization: Bearer <admin-jwt>"
```

## 安全注意

- v4.3 **沒有 sandbox**：plugin 跑在 agent 同 process，有完整 Python 權限。
- 只裝你信任 / 自己 audit 過的 plugin。
- v4.4 規劃中：subprocess 隔離 + 公鑰簽章。
