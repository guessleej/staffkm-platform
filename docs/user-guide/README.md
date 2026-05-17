# staffKM 使用手冊

> 給最終使用者 / 內部 admin / 部署人員的中文操作手冊。
> 開發者文件請看 `/docs/dev/`，部署請看 `/docs/deploy/`。

## 章節

| 對象 | 文件 |
|------|------|
| **第一次用** | [01-first-login.md](./01-first-login.md) — 登入 + 走完 onboarding |
| **使用者** | [02-chat.md](./02-chat.md) — 跟 AI 對話 / 看引用 |
| **使用者** | [03-knowledge-base.md](./03-knowledge-base.md) — 建知識庫 + 上傳文件 |
| **建立應用** | [04-create-app.md](./04-create-app.md) — 從模板 / 從空白 / 進階 workflow |
| **進階** | [05-projects.md](./05-projects.md) — Project 抽象（KB+App 綁一起）|
| **進階** | [06-web-sync.md](./06-web-sync.md) — 從 URL / sitemap 同步外部網頁 |
| **embed** | [07-embed-widget.md](./07-embed-widget.md) — 把 chat 嵌到任何網站 |
| **admin** | [08-admin.md](./08-admin.md) — 使用者 / 模型 / 用量 quota / 設定 |
| **常見問題** | [99-faq.md](./99-faq.md) |

## 一句話介紹

staffKM 是企業 AI 知識管理平台：
- **餵文件**（PDF / Word / Markdown / 網頁）建知識庫
- **配 LLM**（Ollama 地端 / OpenAI / Anthropic / Gemini 等 25+ provider）
- **建應用**（12+ 模板 / 自訂 prompt / 視覺化 workflow）
- **使用者跟它聊**（RAG 自動引用文件，看得到出處）

完整功能對標 MaxKB + claude.ai 風 UI。

## 快速開始

```
1. 開 https://staffkm.example.com → admin / Admin@2026
2. 看完歡迎導覽（30 秒）
3. 從模板建你第一個應用，或
4. 進「知識庫」拖檔上傳 → 切片好之後建應用 → 聊
```

詳細步驟看 [01-first-login.md](./01-first-login.md)。
