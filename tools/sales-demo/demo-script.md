# StaffKM 10 分鐘 Sales Demo — v4.1 A

> 對象：企業 IT 主管 / 知識管理 PM / HR ops
> 環境：本機 docker compose（`./tools/scripts/safe-redeploy.sh --all`）

## 0. 開場（30s）

> 「我先給你看一個剛開戶的客戶，從註冊到 HR bot 上線，全程不到 10 分鐘。」

開瀏覽器 → `http://localhost/signup`

## 1. Trial 註冊（1 分鐘）

填寫：
- Email：`demo@staffkm.example.com`
- 工作區：`StaffKM Demo`
- 密碼：`DemoStaffKM2026!`

按「開始 14 天試用」→ 顯示「試用已開通」+ 到期時間。

> 「免費 14 天，自助開戶，無需業務介入。後台會自動建 workspace、設 admin 角色。」

## 2. 登入 + 進管理後台（30s）

點「前往登入」→ 用剛才 email/password 登入。

預期反應：「比想像中快」

## 3. Starter pack 一鍵安裝（2 分鐘）

進 `/admin` → 「Starter Pack」（v4.2 補 UI，目前用 curl 示範）：

```bash
TOKEN=<從 localStorage.access_token 取>
WS=<從 url 取>
for p in 01-hr-assistant 02-it-helpdesk 03-knowledge-qa 04-meeting-notes 05-sales-knowledge; do
  curl -X POST -H "Authorization: Bearer $TOKEN" -H "X-Workspace-ID: $WS" \
       http://localhost/api/v1/admin/starter-pack/$p/install
done
```

回 `/applications` → 看到 5 個應用瞬間出現。

> 「這 5 個是我們最常被問的場景：HR / IT / 通用 QA / 會議紀要 / 銷售。
>  全部 workflow 已連好，你只要上傳文件就能用。」

## 4. 上傳 HR 文件（2 分鐘）

點「HR 助理」→ 進入應用 → 切到「知識庫」tab → 拖一份 PDF（公司請假規則）→ embedding 自動跑。

切到「測試」tab：
- 問：「我要怎麼請特休？」
- LLM 串流回答 + 引用編號

> 「索引完成只要幾秒，回答帶引用，員工自己就能查。」

## 5. 銷售知識（2 分鐘）

切到「銷售知識助理」→ 上傳一份產品比較表 → 問：「我們的旗艦版跟競品 X 差在哪？」

> 「業務帶平板進 client meeting 隨時查，不用回頭問 PM。」

## 6. 觀測與成本（1 分鐘）

進 `/admin/billing` → 看 per-user token 用量 + USD 試算
進 `/admin/quotas` → 設「每使用者每日 50k token」

> 「成本完全透明，超量自動 throttle。」

## 7. 收尾 Q&A（1 分鐘）

預期常見問題：

| Q | A |
|---|---|
| 私有部署？ | 是，全 self-hosted；docker compose 或 K8s helm chart |
| 用什麼 LLM？ | 預設 Ollama 本機；也接 OpenAI / Claude / Gemini |
| 多租戶？ | workspace 級隔離 + RBAC 4 級（owner/admin/editor/viewer） |
| 14 天到期會怎樣？ | workspace 自動凍結（trial_expiry_worker），資料保留 30 天 |
| 怎麼升級付費？ | v4.7 補 billing 接口；目前聯絡業務 |

## 8. 下一步

- 留 email → 寄完整 deployment guide（docs/deploy/）
- 安排 30 分鐘 technical deep-dive：workflow editor / MCP / multi-model
- 試用滿意 → 簽 POC contract（v3.0 audit log 滿足合規）

---

**Tips：**
- 全程不超過 10 分鐘；遇到問題直接 demo 真實 bug（不要假裝）
- 強調「**這是你 14 天免費試用內可以做到的**」
- 不要 demo workflow editor 細節 — 留 deep-dive
