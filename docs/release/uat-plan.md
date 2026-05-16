# UAT Plan v2.0.0

> 在 stage 上邀 4 個 persona 各 2~3 人進行 1 小時 hands-on，
> 驗證使用者真的能完成核心 JTBD。對應 `docs/ux/personas.md`。

## 1. 受測 persona × 人數

| Persona     | 角色           | 人數 | 任務集           |
| ----------- | -------------- | ---- | ---------------- |
| P1 依潔     | 行政專員       | 3    | T1 / T2 / T3     |
| P2 Kevin    | 數位轉型 PM    | 2    | T4 / T5 / T6     |
| P3 家豪     | IT 主任        | 2    | T7 / T8 / T9     |
| P4 淑芬     | 部門主管       | 2    | T10              |

## 2. 任務集

### P1 — 行政專員
- **T1**：找「請假申請流程」，30 秒內回答（含 citation）
- **T2**：問「我可以連休幾天」追問
- **T3**：在「對話歷史」找回 3 天前的某次討論

### P2 — PM
- **T4**：建立一個簡易問答 application，綁到「員工守則」KB
- **T5**：用 workflow 編輯器加 LLM + condition + answer 三節點
- **T6**：歷史版本抽屜回滾到前一版

### P3 — IT 主任
- **T7**：開 `/admin/usage`，看本月 token / cost
- **T8**：把 quota 設成 month_token_cap=10，重發一次 chat 確認 429
- **T9**：在 `/admin/models` 切換 gateway 預設 model

### P4 — 部門主管
- **T10**：登入 → 預設首頁進入對話 → 不需任何指導完成一次有效對話

## 3. 評分

每個任務由觀察員打三項：

| 指標     | A（很順）   | B（會卡但完成） | C（完全沒做出來）  |
| -------- | ----------- | --------------- | ------------------ |
| 完成度   | 全做完      | 完成主要        | 卡在前段           |
| 順暢度   | 沒卡        | 1-2 處遲疑      | 多處需提示          |
| 滿意度   | 推薦同事    | 願意自己用      | 不會主動用         |

## 4. Go / No-Go

- **Go 條件**：所有 P1+P4（核心 9 個 task）≥ B 等；P2/P3 ≥ B 等 7/9 個任務
- **No-Go**：任一 P1 task 出 C 等 → 阻擋；P2/P3 出 C 等 ≥ 2 → 阻擋並修

## 5. 發現處理

- 每個 issue 24h 內開 GitHub Issue + 標 `uat-finding`
- P1 issue → 阻擋 release；P2 issue → 進 v2.0.1 patch；P3 issue → backlog

## 6. 時程

| 階段         | 日期          | 負責            |
| ------------ | ------------- | --------------- |
| stage 環境就緒| pre-release D-5 | DevOps         |
| 受測者招募   | D-4 ~ D-3     | PM              |
| 跑 UAT       | D-2 ~ D-1     | UX + PM 各一觀察員 |
| 整理結果     | D-0           | PM              |
| Go / No-Go   | D-0 17:00     | Eng Lead + PM   |
