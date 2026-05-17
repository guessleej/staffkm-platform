# FAQ — 常見問題

## 使用者

**Q. 為什麼 AI 回答跟我預期不一樣？**
A. 三個原因：
1. KB 沒檢索到對的段落 → 用「命中測試」debug
2. LLM 沒拿到完整 prompt → 看 App 設定的 `system_prompt`
3. LLM 本身能力限制 → 換更強模型

**Q. 我傳了 PDF 但 AI 不知道內容**
A. 看文件 status：
- `pending` / `processing` → 還沒切片完，等等
- `error` → hover 看錯誤；常見：加密 PDF / 影像 PDF（用 OCR）
- `ready` → 看 App 有沒有勾這個 KB

**Q. 引用 chip 點開沒內容**
A. 該段段落沒有 content 欄位（罕見），看 hover popover 內容；若都空 → admin 查 paragraphs 資料

**Q. 切了 Project 為何訊息 title 沒變？**
A. Project scope 只影響「新對話」；既有對話 freeze 在 create 當下。新開一個就會帶。

**Q. 我能在手機用嗎？**
A. 響應式設計，能用但體驗一般。原生 App 不在 roadmap。

## 建立應用

**Q. 「立即試用」跟「使用此模板」差在哪？**
A. 試用 = 不真建 App，只給你看模板效果。建立 = 真建 App 進 DB。

**Q. 「存模板」會把 KB 也存進去嗎？**
A. 不會。只存 prompt + 開場白 + 範例問題 + 「是否需要 KB」旗標。下次用此模板要重選 KB。

## Workspace / 多租戶

**Q. 一個 user 可以在多 workspace 嗎？**
A. 可以；切 workspace 用頂 nav picker。每個 workspace 資料完全隔離。

**Q. owner / admin / editor / viewer 差別？**
A. owner = workspace 全權；admin = 不能改 owner / 不能刪 workspace；editor = 能建/編 App + KB；viewer = 只能看 + chat。

## 部署 / 維運

**Q. 怎麼上 production？**
A. `docs/deploy/production-deploy.md` 完整 runbook（Caddy auto-TLS 一行起）。

**Q. 備份去哪了？**
A. `/var/lib/staffkm/backups/{postgres,minio}/`。可設 `BACKUP_S3_URL` 推異地。詳見 `docs/deploy/backup-restore.md`。

**Q. 怎麼看 LLM 用量？**
A. `/admin/usage`；或進 Grafana。

**Q. 接 Google / Microsoft SSO？**
A. 設 `OIDC_*` 環境變數，重啟 auth + gateway。LoginView 自動冒「使用 SSO 登入」按鈕。詳見 `.env.production.example`。

## 整合

**Q. 嵌到我們公司 portal**
A. 看 [07-embed-widget.md](./07-embed-widget.md)，一行 `<script>` 搞定。

**Q. 用 API 呼叫**
A. App 卡片 → API Key → 生 key → POST `/api/v1/applications/{id}/chat` (Bearer)。

**Q. 接 LINE / Teams**
A. 後端有 webhook 預留路徑 `/api/v1/integrations/{line,teams}/webhook`，但 message handler 還沒做完（v3 候選）。

## Debug

**Q. 怎麼看 backend log？**
A. `docker compose ... logs -f --tail=200 agent`

**Q. 怎麼看 task queue？**
A. `docker exec staffkm-prometheus wget -qO- http://localhost:9090/api/v1/query?query=celery_task_pending_total`（待加 celery exporter）

**Q. 一直 502**
A. 通常是 rebuild 後 nginx upstream IP 過期 — `./tools/scripts/safe-redeploy.sh ui` 會強制 recreate nginx。

---

回 [README](./README.md)
