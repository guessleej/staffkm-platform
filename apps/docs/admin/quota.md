# Quota 與用量

## 設定

`/admin/usage`（admin 角色才看得到）：
- **Monthly token cap**：所有模型加總；超過直接 429
- **Monthly cost cap (USD)**：成本上限；超過直接 429

留空 = 無上限。

## 計帳精度

- v2.0：**tiktoken** 精算；fallback 到 char/4（未裝 tiktoken 時）
- v2.1（計畫）：直接拿 provider 官方 usage 回傳，100% 精確

## 429 行為

- 任一 cap 達到 → 新 chat 請求回 `429 Too Many Requests`
- header 帶 `Retry-After`（下個月初）
- 不影響已啟動的 SSE stream

## API

```bash
# 取
curl -H "Authorization: Bearer $KEY" \
  https://staffkm.example.com/api/v1/workspace/$WS/quota

# 設
curl -X PUT -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"monthly_token_cap": 5000000, "monthly_cost_cap_usd": 200}' \
  https://staffkm.example.com/api/v1/workspace/$WS/quota
```

CLI：

```bash
staffkm quota set --tokens 5000000 --cost 200
staffkm usage summary
```

## 警告 / 限流策略

- 70% → 進度條黃
- 90% → 進度條紅 + dashboard 提示
- 100% → 429（並建議 admin 收信告警；M5 中段補）
