# Webhooks（M4 Event Trigger）

支援兩種觸發來源：

| Kind     | 用途                       |
| -------- | -------------------------- |
| interval | 每 N 秒跑一次              |
| cron     | crontab 表達式             |
| webhook  | 對外 HTTP endpoint 收事件   |

## 建立

```bash
curl -X POST -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{
    "application_id": "<app-id>",
    "name": "每日彙整",
    "kind": "cron",
    "cron_expr": "0 9 * * *",
    "input_template": "請整理今天的會議結論"
  }' \
  https://staffkm.example.com/api/v1/workspace/$WS/triggers
```

## Webhook receiver（M5 中段補）

預計：

```
POST /api/v1/public/triggers/{trigger_id}/fire
Header X-Trigger-Signature: HMAC-SHA256(body, secret)
```

簽章驗證後寫 `event_trigger_runs(status='queued')`，由 dispatcher 拉走執行。

## 查詢執行歷史

```bash
curl -H "Authorization: Bearer $KEY" \
  https://staffkm.example.com/api/v1/workspace/$WS/triggers/$TID/runs
```
