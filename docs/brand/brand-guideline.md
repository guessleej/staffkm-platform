# staffKM Brand Guideline v1

| 版本    | 內容                                       |
| ------ | ------------------------------------------ |
| v1.0   | M1 收尾建立；之後依使用回饋逐版迭代          |
| 維護者 | Design Lead（暫由 RFC-007 簽署人代理）     |

## 1. 品牌核心

**staffKM** = staff + Knowledge Management
> 內部行政人員的智能知識協作平台 —「**讓組織知識被找得到、用得上、留得下**」。

| 維度    | 描述                                                                                  |
| ------- | ------------------------------------------------------------------------------------- |
| Mission | 把分散在 email / Slack / wiki / SOP 的內部知識，透過 AI 整合成「可問答 + 可工作流」的能力 |
| Tone    | 專業、克制、可信賴；不浮誇、不裝可愛；繁體中文台灣腔                                  |
| Voice   | 像一個資深同事：直接、提要點、不繞圈、預設使用者很忙                                  |
| 禁忌    | emoji 灌水、AI 味行銷詞（「賦能 / 一站式 / 智慧解決方案」）、超寬鬆 padding           |

## 2. Logo 系統

### 2.1 三個變體

| 變體        | 用途                                          | 檔案                             |
| ----------- | --------------------------------------------- | -------------------------------- |
| Mark        | favicon / 角落小圖 / 對話頭像                 | `assets/logo-mark.svg`           |
| Wordmark    | 純文字場合（footer / 法律頁）                 | `assets/logo-wordmark.svg`       |
| Lockup      | 預設組合（mark + wordmark）；header / 啟動畫面 | `assets/logo-lockup.svg`         |

### 2.2 使用規則

- **最小寸法**：Mark ≥ 24px、Lockup ≥ 96px 寬。低於此值換 Mark。
- **clear-space**：四周保留至少 0.5 個 mark 寬度的空白，不可被其他元素緊貼。
- **顏色**：預設深色 (`hsl(240 64% 50%)`)；深底時用 `--color-neutral-50` 反白。
- **禁止**：拉伸 / 加陰影 / 加 outline / 換 typeface / 自己改顏色。

### 2.3 favicon

`apps/web/public/favicon.svg` 為 Mark 16×16 簡化版（去 stroke-detail）。

## 3. Color System（對應 design-tokens）

| 角色      | Token                | HSL                | 用途                                  |
| --------- | -------------------- | ------------------ | ------------------------------------- |
| Brand     | `--color-brand-600`  | `240 64% 50%`      | 主要 CTA / 連結 / focus ring         |
| Brand 強  | `--color-brand-700`  | `242 58% 42%`      | hover                                 |
| Neutral 背景 | `--color-surface-base` | `0 0% 99%`     | 主背景（light）                       |
| Neutral 卡 | `--color-surface-raised` | `0 0% 100%`  | 卡片 / dialog 背景                   |
| Success   | `--color-success-600`| `142 71% 38%`      | 成功 / 啟用 badge                    |
| Warning   | `--color-warning-600`| `38 92% 50%`       | 用量 70% 警示                        |
| Danger    | `--color-danger-600` | `0 84% 55%`        | 刪除 / 用量 90% / 嚴重錯誤           |
| Info      | `--color-info-600`   | `199 89% 48%`      | 中性資訊提示                         |

**對比規則**：
- 文字 vs 背景 ≥ WCAG AA（4.5:1）
- 大字 / icon ≥ AA Large（3:1）
- focus ring 必須對任何背景可見（用 `outline` + `outline-offset`，不用 box-shadow）

## 4. Typography

| 角色   | Font                                          | 大小範圍 | 用途           |
| ------ | --------------------------------------------- | -------- | -------------- |
| Sans   | `Inter, -apple-system, "Noto Sans TC", sans`  | 12~32px  | 預設           |
| Mono   | `"JetBrains Mono", "SF Mono", monospace`      | 11~14px  | code / token ID |
| Headline | Inter 600 / 700                             | 18~32px  | 標題          |

繁體中文 fallback 為 `Noto Sans TC`；不指定字重時用 400；標題 600；超大 H1 才 700。

## 5. Iconography

- 統一用 stroke-based icons（24×24 viewBox、stroke-width=2）
- 預設 `text-neutral-500`，hover `text-neutral-700`
- 不混用 filled icons（避免風格不一）

## 6. Voice & Microcopy

**正面範例**
- 「**檔案已刪除**」（直述完成）
- 「**確定要回滾到 v3？回滾前會自動快照**」（說明後果）

**反面範例**
- 「親愛的使用者您好，您的檔案已順利完成刪除作業 ✨」（多餘禮節 + 表情符號）
- 「我們為您智慧地完成這項操作」（AI 味）

## 7. 應用範例（do / don't）

```
✓  bg-brand-600 text-white  primary CTA
✓  bg-surface-raised border border-neutral-200 rounded-xl  卡片
✓  text-danger-600 hover:bg-danger-50  刪除動作

✗  漸層 + 玻璃擬態 + 大量 emoji（不符合 staffKM 沉穩調性）
✗  brand 色用於非互動的純裝飾（保留為「可點」的視覺信號）
```

## 8. 變更管理

修改本指南需開 RFC（沿用 `docs/rfc/RFC-TEMPLATE.md`），重大顏色 / logo 變動需：
- 影響範圍 review（含暗色模式）
- design-tokens PR 同步
- 設計師 + Eng Lead 雙簽

---

> 第一版焦點是「**把禁忌列清楚**」，比追求完美視覺重要。下一版（v1.1）會補：插畫風格指引、空狀態圖示、品牌字型授權說明。
