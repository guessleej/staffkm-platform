## 摘要

<!-- 一段話：這個 PR 做了什麼、為什麼 -->

Closes #

## 變更類型

- [ ] feat（新功能）
- [ ] fix（bug 修復）
- [ ] refactor（不影響行為的重構）
- [ ] docs（文件）
- [ ] chore（雜項 / 依賴）
- [ ] test（測試）
- [ ] perf（效能）
- [ ] breaking（破壞性變更）

## 怎麼測

<!-- 列出 reviewer 可以驗證的步驟 -->

```bash
# 例：
make test-be
curl -X POST http://localhost:8001/api/v1/...
```

## 截圖 / 影片（UI 改動時）

| Before | After |
|--------|-------|
| …      | …     |

## 影響範圍

- [ ] DB schema（已附 migration）
- [ ] API（已更新 OpenAPI）
- [ ] 環境變數（已更新 `.env.example`）
- [ ] 依賴（已更新 lock 檔）
- [ ] Docker（已更新 Dockerfile / compose）

## DoD 檢核

- [ ] 通過 lint / 型別 / 測試
- [ ] 覆蓋率 ≥ 80%
- [ ] 沒有 hard-coded secret
- [ ] 文件 / changelog 已更新
- [ ] log / metric / trace_id 已加
- [ ] 對應 RFC 已 merge（若是重大改動）
- [ ] 回滾方式已記錄

## 回滾步驟

<!-- 萬一上線壞了，怎麼回？ -->

1. revert this PR
2. 若有 DB migration：…

## Reviewer 注意事項

<!-- 哪段值得多看？哪段不確定？ -->

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
