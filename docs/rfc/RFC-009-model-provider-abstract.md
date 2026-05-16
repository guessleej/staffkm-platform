# RFC-009 — Model Provider 抽象介面（M3 啟動）

| 項目      | 內容                                           |
| --------- | ---------------------------------------------- |
| 狀態      | Draft（M3 啟動，scaffold 合進 main）           |
| 提案日期  | 2026-05-16                                     |
| 對應里程碑 | M3 — Model Hub GA                             |
| 相關 PR   | feat/m3-model-provider-abstract                |

## 1. 動機

目前 `application_agent._init_llm_from_db()` 直接 `AsyncOpenAI(...)`，
所有 provider 都假裝是 OpenAI-compatible。對於：

- Anthropic（messages API + tools 不同）
- AWS Bedrock（boto3 + SigV4）
- Google Gemini / Vertex AI（generateContent endpoint）
- Cohere（chat 格式不同）

…都無法正確接入。M3 要做到「20+ provider，可在 UI 下拉選擇」，必須先把
provider 抽象起來，否則後續每加一家就要再改一次 agent 主程式。

## 2. 設計

### 2.1 模組佈局

```
services/agent/app/core/providers/
├── __init__.py        # 對外 export
├── base.py            # BaseProvider ABC + ChatRequest / ChatResponse / EmbedRequest dataclass
├── openai_compat.py   # 走 AsyncOpenAI 的萬用 adapter
└── registry.py        # 20+ provider metadata + get_adapter()
```

### 2.2 BaseProvider 介面

```python
class BaseProvider(ABC):
    provider_type: str = ""

    def __init__(self, api_key, base_url=None, config=None): ...

    async def chat(self, req: ChatRequest) -> ChatResponse: ...     # 必實作
    async def chat_stream(self, req) -> AsyncIterator[str]: ...     # 預設 fallback
    async def embed(self, req: EmbedRequest) -> EmbedResponse: ...  # 預設 NotImplementedError
    async def health(self) -> bool: ...                              # 預設 True
```

### 2.3 Registry

`PROVIDER_REGISTRY` 列出 20+ provider，每筆有：
`type / label / adapter_type / default_base_url / recommended_models / needs_api_key / notes`。

涵蓋：
- **地端**：Ollama（預設）、vLLM、Xinference、LocalAI
- **國際雲**：OpenAI、Azure OpenAI、Anthropic、Bedrock、Gemini、Vertex AI、Cohere、Mistral、Groq、Together、Perplexity、OpenRouter
- **中文 / 亞洲**：DeepSeek、智譜 GLM、Moonshot Kimi、通義千問、Baichuan、MiniMax、SiliconFlow、01.AI Yi、字節豆包

### 2.4 API

`GET /api/v1/workspace/{ws}/model-providers/registry` → 回上述 metadata 陣列，
前端建立 model_provider 時用來填下拉與預設 base_url。

## 3. 範圍切割

| 階段      | 內容                                                           |
| --------- | -------------------------------------------------------------- |
| M3 啟動（本 PR） | BaseProvider + OpenAICompatProvider + Registry + GET registry |
| M3 中段   | 接入 application_agent，把 `_init_llm_from_db` 改用 `get_adapter` |
| M3 中段   | 補 Anthropic / Bedrock / Gemini / Cohere 專屬 adapter         |
| M3 收尾   | Token 計帳 + Quota + 統計儀表板（P3-W9-11）                    |

## 4. 風險與權衡

- **fallback 到 OpenAICompatProvider**：尚未實作的 adapter_type 暫退回，避免執行期報錯。
  代價是這些 provider 在 M3 中段補完前實際無法跑非 OpenAI-compat 端點，但介面層已就緒。
- **api_key 加密**：本 PR 仍沿用 `api_key_enc` 明文欄位（既有設計）。M3 收尾再導入 KMS。
- **硬鎖 gemma4:e4b**：staffKM 的全域硬鎖規則不受本 PR 影響；Provider 抽象只負責「能呼叫」，
  「是否被允許」仍由 application 層的 model_id 約束。
