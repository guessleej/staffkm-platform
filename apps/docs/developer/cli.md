# CLI（staffkm）

```bash
pip install staffkm-cli
```

## 設定

任一：

```bash
export STAFFKM_BASE_URL=https://staffkm.example.com
export STAFFKM_API_KEY=sk-...
export STAFFKM_WORKSPACE_ID=...
```

或每次帶旗標：`staffkm --base-url ... --api-key ... --workspace ... <cmd>`

## 指令

```bash
staffkm ping                                  # 健康檢查
staffkm apps list                             # 列出應用
staffkm chat --app-id <id> "今天天氣？"        # SSE 串流
staffkm chat --app-id <id> --no-stream "..."  # 一次性回傳
staffkm usage summary                         # 當月用量
staffkm usage logs --page 1 --page-size 20
staffkm quota get
staffkm quota set --tokens 5000000 --cost 200
```

## 自動化範例

```bash
# 每天早上把 token usage 寫到 monitoring channel
staffkm usage summary | jq '.usage.tokens' \
  | xargs -I{} curl -X POST $SLACK_WEBHOOK \
      -d "{\"text\":\"今日累積 tokens: {}\"}"
```
