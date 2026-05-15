# RFC-005: On-premise LLM First — 地端優先策略

| 欄位 | 內容 |
|------|------|
| 編號 | RFC-005 |
| 提案者 | @architect |
| 狀態 | Draft |
| 建立日期 | 2026-05-15 |
| Reviewers | @lead-be @pmp @security |
| 相關 | RFC-002 (Workflow Engine), RFC-001 (Multi-tenant) |

---

## 1. 摘要

把 LLM 預設從 OpenAI 改為**內網 Ollama**（`gemma4:e4b`），所有節點 / 應用 / 範例 workflow 預設指向地端 endpoint。雲端 provider（OpenAI / Anthropic / Gemini …）改為**選用**，需要 workspace owner 主動啟用、補 API key 才能用。Embedding（bge-m3）已是地端，本案把 LLM 對齊。

## 2. 動機

行政 / 政府 / 企業內網場景的硬性需求：
- **資料主權**：簽呈、規格書、人事資料**不可外送**第三方
- **法遵**：個資法、政府資安規範禁止把內部文書送雲端 API
- **成本可控**：地端推論一次性硬體投資 < 雲端 API 月費滾動
- **離線運作**：部分客戶（軍警、醫療、金融）內網無法連外
- **可用性**：不依賴外部 API 的 SLA / rate limit / outage

過去依賴 OpenAI 造成的問題（已實際遭遇）：
- DNS 解析失敗無法處理文件（內網 backend network `internal: true`）
- API key placeholder 造成 silent fail
- 「Connection error」訊息對行政使用者完全不可解
- 月費難預測（一個小工作流測試就吃幾十美元）

## 3. 目標與非目標

**目標**
- [ ] G1：所有節點 / 應用 / Workflow 範本**預設**指向地端 LLM endpoint
- [ ] G2：`docker compose up` 完成後**不需任何外部 API key** 即可完整跑通 RAG 對話
- [ ] G3：地端模型至少支援 **繁體中文 + Function Calling + 32K context**
- [ ] G4：雲端 provider 仍可選用，但需明確 opt-in（UI 上「啟用外部模型」開關）
- [ ] G5：所有官方範例 workflow 用地端模型錄製、文件以地端為主軸
- [ ] G6：Model Hub UI 把地端 provider 排在最前、雲端折疊收起

**非目標**
- N1：不禁用雲端 provider（用戶仍可選用 GPT-4 / Claude，只是非預設）
- N2：不做 GPU 自動偵測（v2 假設用戶自己選對 model size）
- N3：不做地端模型 fine-tuning（Phase 6+）

## 4. 提案設計

### 4.1 預設 Stack

| 角色 | 預設模型 | Provider | 大小 | 備註 |
|------|---------|----------|------|------|
| **LLM (chat / agent / vision)** | `gemma4:e4b` | Ollama | ~9.6 GB | Google Gemma 4 E4B、4.5B 有效 / 8B 含 embedding、140+ 語言、128K context、文/圖/音多模態、Apache-2.0 |
| **Embedding** | `bge-m3` | Ollama | ~1.2 GB | 1024 維、多語言（已部署） |
| **Reranker**（選用） | `bge-reranker-v2-m3` | TEI / 自架 HTTP | ~1.4 GB | 進 Phase 3 |
| **Vision**（選用） | `gemma4:e4b`（內建） | Ollama | 同上 | Gemma 4 原生支援圖像 + 音訊；Phase 4 啟用 |
| **STT**（選用） | `whisper-cpp / faster-whisper` | 自架 HTTP | varies | 進 Phase 4；若 Gemma 4 音訊夠用可省 |
| **TTS**（選用） | `coqui-tts` 或 OpenedAI-Speech | 自架 HTTP | varies | 進 Phase 4 |

### 4.2 為何選 gemma4:e4b

| 候選模型 | 多語言 | Tools | Context | 多模態 | 大小 | 授權 | 結論 |
|---------|:---:|:---:|:---:|:---:|:---:|------|------|
| **gemma4:e4b** | ⭐⭐⭐⭐⭐ (140+) | ✅ | **128K** | ✅ 文/圖/音 | 9.6 GB | Apache-2.0 | **採用** |
| gemma4:e2b | ⭐⭐⭐⭐ | ✅ | 128K | ✅ | 7.2 GB | Apache-2.0 | 輕量替代（hardware fallback） |
| gemma4:26b | ⭐⭐⭐⭐⭐ | ✅ | 256K | ✅ | 18 GB | Apache-2.0 | 企業級升級選項 |
| qwen2.5:7b | ⭐⭐⭐⭐⭐ | ✅ | 32K | ❌ | 4.7 GB | Apache-2.0 | 純文字 RAG，輕量替代 |
| llama3.2:3b | ⭐⭐ | ✅ | 128K | ❌ | 2 GB | Llama 3.2 | 英文小型機 |
| mistral-nemo:12b | ⭐⭐⭐ | ✅ | 128K | ❌ | 7.1 GB | Apache-2.0 | 中文偏弱 |

選 **`gemma4:e4b`** 的理由：
- **140+ 語言**：覆蓋繁體中文、簡體中文、英、日、韓、東南亞語系，行政文書最廣
- **128K context**：可一次塞入長簽呈、規格書、會議記錄全文
- **文/圖/音三模態原生支援**：未來 Phase 4 vision / 語音節點不用另開模型容器
- **內建 thinking mode**：複雜推理品質提升（可動態開關，降低成本）
- **Function calling 原生支援**：適合 workflow 工具節點
- **Apache 2.0 授權**：商用、私有化部署無顧慮
- **Google 官方維護**：長期支援預期穩定

`qwen2.5:7b` 仍列為**輕量替代**選項（純文字場景效能較高、模型較小），但 Gemma 4 多模態 + 長 context + 多語言的整合價值在企業環境綜合勝出。

### 4.3 Architecture

```
┌────────────────────────────────────────────────────┐
│                    User Browser                    │
└────────────────────────┬───────────────────────────┘
                         │
                  ┌──────▼──────┐
                  │   Nginx     │ (port 80)
                  └──────┬──────┘
                         │
              ┌──────────┴───────────┐
              │     Gateway (8000)   │
              └──────────┬───────────┘
                         │
        ┌────────┬───────┼────────┬────────┐
        ▼        ▼       ▼        ▼        ▼
     auth   knowledge  agent    chat    integration
                 │        │
                 │        │
                 ▼        ▼
        ┌─────────────────────┐    ┌──────────────────┐
        │  embedder (Ollama)  │    │ External LLM API │
        │ ┌─────────────────┐ │    │ (OpenAI / Claude │
        │ │ bge-m3 (embed)  │ │    │  / Gemini …)     │
        │ │ gemma4:e4b(LLM) │ │    │  ↑ 選用，需 key   │
        │ └─────────────────┘ │    │  ↑ 預設不啟用     │
        │   ↑ 內網、預設       │    └──────────────────┘
        └─────────────────────┘
```

### 4.4 預設 .env

```bash
# ── LLM (預設地端 Ollama) ─────────────────────
LLM_PROVIDER=ollama
LLM_MODEL=gemma4:e4b
LLM_BASE_URL=http://embedder:11434/v1
LLM_API_KEY=dummy

# ── Embedding (地端) ─────────────────────────
EMBEDDING_MODEL=bge-m3
EMBEDDING_BASE_URL=http://embedder:11434/v1
EMBEDDING_DIMENSION=1024

# ── 雲端 LLM (選用，預設關閉) ────────────────
# OPENAI_API_KEY=
# ANTHROPIC_API_KEY=
# GOOGLE_API_KEY=
```

### 4.5 配置層級（從 fallback 上溯）

```
1. Workflow Node 個別 config（最高）
2. Application 設定
3. Workspace 預設模型
4. System 預設（LLM_MODEL）  ← gemma4:e4b
```

### 4.6 程式介面

```python
# packages/python/staffkm-providers/llm.py
def get_default_llm() -> BaseLLM:
    if settings.LLM_PROVIDER == "ollama":
        return OllamaLLM(
            base_url=settings.LLM_BASE_URL,
            model=settings.LLM_MODEL,
        )
    if settings.LLM_PROVIDER == "openai":
        if not settings.OPENAI_API_KEY:
            raise ConfigError("OPENAI_API_KEY 未設定，回退到地端 Ollama")
        return OpenAILLM(...)
```

`get_default_llm()` 失敗時**自動 fallback 到地端**並 log warning，**絕不 silent fail**。

### 4.7 UI/UX

- **應用建立精靈** 第一步：「使用地端模型 (推薦)」radio button 預設選中，雲端模型在「進階」區塊
- **Model Hub** 排序：地端 → 國內 → 國際雲端
- **首次設定**：歡迎頁明確告知「您的資料完全在內網處理，未連任何外部 API」

## 5. 替代方案

| 方案 | 優點 | 缺點 | 為何不選 |
|------|------|------|----------|
| 維持 OpenAI 預設 | 易上手、品質高 | 違反資料主權、成本不可控 | 違反 G1-G6 |
| 預設 Anthropic | 品質好 | 同樣外送 | 違反 G1 |
| 預設 vLLM | 推論快 | 部署複雜、ARM 支援差 | Mac 開發機跑不動 |
| 預設 LM Studio | UI 友善 | 不適合容器化部署 | 違反 docker-first |
| **預設 Ollama gemma4:e4b（本案）** | **ARM/x86、容器化、中文強** | 7b 推論速度有限 | **採用** |

## 6. 風險與緩解

| 風險 | 機率 | 衝擊 | 緩解 |
|------|------|------|------|
| 地端 LLM 推論慢，使用者體驗差 | 高 | 中 | UI 顯示「地端 / 雲端」切換 chip；提供「升級到 14b」CTA；配 streaming |
| 7B 模型對複雜 reasoning 不足 | 高 | 中 | 範本工作流提示「複雜推理可切 14b 或 GPT-4」；reranker 補強 RAG 品質 |
| 用戶硬體跑不動 7B | 中 | 高 | 提供 `qwen2.5:1.5b` minimal preset；docs 註明硬體需求（≥ 16GB RAM） |
| Ollama 套件 bug 影響核心 | 中 | 高 | Provider 抽象層 + 自動 fallback；定期更新但鎖小版 |
| 既有測試環境用 OpenAI | 中 | 低 | env override：CI 跑地端、開發者個人可用雲端；migration guide |
| 文件 / 教學影片要重錄 | 確定 | 中 | Phase 5 統一錄製；過渡期文件雙寫 |

## 7. 影響範圍

- **既有 code**：`services/agent/app/config.py`、`services/agent/app/core/workflow/executor.py`、`apps/web/src/components/workflow/lf-nodes.ts`、`NodeConfigPanel.vue`、`ModelProviderView.vue` 都需改預設
- **`.env` / `.env.example`**：刪除 `OPENAI_MODEL` default、新增 `LLM_*` 變數族
- **docker-compose**：在現有 `embedder-init` 之後加 `llm-init` 把 gemma4:e4b pull 下來
- **首次啟動**：多下載 4.7GB 模型（~30 分鐘 @ 中速網路）
- **記憶體需求**：embedder 容器從 4GB 上修到 8GB（bge-m3 + gemma4:e4b）

## 8. 推出計畫

- [ ] **Stage 1**（本 PR）：寫 RFC、改 default config、加 llm-init service、更新 .env.example
- [ ] **Stage 2**（Phase 3 Provider 抽象）：實作 fallback 邏輯、UI 切換器
- [ ] **Stage 3**（Phase 5）：重錄所有教學素材以地端為主

回滾：env 改 `LLM_PROVIDER=openai` + `OPENAI_API_KEY=...` 即可秒切。

## 9. 量測指標

- **採用**：Stage 1 上線 30 天，>= 80% 新建 application 預設用地端
- **品質**：地端 RAG 命中率（人工評估）≥ 75%（vs 雲端 ≥ 88%）
- **效能**：gemma4:e4b on Apple M3 / 16GB RAM：TTFT < 3s、tokens/s ≥ 25
- **成本**：新用戶 30 天 OpenAI API 費用為 0（除非主動 opt-in）

## 10. 開放問題

- [ ] Q1：要不要在 docker-compose 提供 GPU profile（vLLM）讓有卡的用戶跑更大模型？@devops
- [ ] Q2：Model Hub 是否預載「下載中文 14b」一鍵升級？@ux
- [ ] Q3：法規說明文案要哪個版本（個資法 / 政府資安通則）？@pmp 跟法務確認

## 11. 參考資料

- [Qwen2.5 官方](https://qwenlm.github.io/blog/qwen2.5/)
- [Ollama Model Library](https://ollama.com/library)
- [bge-m3 (BAAI)](https://huggingface.co/BAAI/bge-m3)
- 個資法、政府資安通則
- 相關：RFC-002 (Workflow), RFC-001 (Multi-tenant)
