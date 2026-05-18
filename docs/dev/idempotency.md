# Idempotency-Key（v3.6）

對任何 staffKM POST API，傳 header `Idempotency-Key: <unique-string>`，
同 key+endpoint 在 **24 小時** 內重複呼叫會直接回原 response，不重跑 handler。

## 用途
- 網路 retry 防重複扣款 / 重複建檔
- mobile / 不穩網路 client 友善
- 自動化 script 重跑安全

## 不支援的 endpoint
- streaming（chat / SSE / `/stream/*` / `/run/*`）— response 不是 single block
- 5xx response — client 應重試，不快取
- 非 JSON response — 不快取

## 範例

```bash
# 第一次：執行真的 handler
curl -X POST http://localhost/api/v1/.../applications \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Workspace-ID: $WS" \
  -H "Idempotency-Key: client-uuid-abc123" \
  -d '{"name": "demo"}'

# 第二次（24h 內）：拿到 cached response + Idempotency-Replayed: true header
curl -X POST http://localhost/api/v1/.../applications \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Workspace-ID: $WS" \
  -H "Idempotency-Key: client-uuid-abc123" \
  -d '{"name": "demo"}'
# → 回原本的 response、header 有 Idempotency-Replayed: true
```

## key 設計建議
- client 生 UUIDv4 一次 + retry 用同一個
- 不要重用（不同邏輯操作用不同 key）
- 長度 ≤ 128 字元

## 清理
expired rows 不會自動刪。建議 cron job：
```sql
DELETE FROM idempotency_keys WHERE expires_at < now();
```
（每天跑一次足以；v3.7 計畫加 worker auto-clean）

## 觀測
- middleware log event: `idempotency_hit` / `idempotency_stored`
- response header `Idempotency-Replayed: true` 表示這次是 cached 回應
