"""LLM model pricing — USD per 1k tokens (2026-05 snapshot).

key = model_name (對應 ai_models.model_name)
ollama / self-hosted = 0
不在表內 = NULL（caller 不要硬給 0、保持 NULL 讓 UI 顯示「未定價」）
"""
MODEL_PRICING: dict[str, tuple[float, float]] = {
    # OpenAI
    "gpt-4o":              (0.0025, 0.01),
    "gpt-4o-mini":         (0.00015, 0.0006),
    "gpt-4-turbo":         (0.01, 0.03),
    "gpt-3.5-turbo":       (0.0005, 0.0015),
    "o1-preview":          (0.015, 0.06),
    "o1-mini":             (0.003, 0.012),
    # Anthropic
    "claude-3-5-sonnet-20241022": (0.003, 0.015),
    "claude-3-5-haiku-20241022":  (0.0008, 0.004),
    "claude-3-opus-20240229":     (0.015, 0.075),
    # Google
    "gemini-1.5-pro":      (0.00125, 0.005),
    "gemini-1.5-flash":    (0.000075, 0.0003),
    # Embedding (input only — completion 設 0)
    "text-embedding-3-small": (0.00002, 0),
    "text-embedding-3-large": (0.00013, 0),
    "bge-m3":                  (0, 0),
    # Ollama / self-hosted：地端模型一律免費，不在此寫死名稱（動態同步），
    # 查無價格的 model 預設 0 元由 meter 端處理。
    # v5.7 — 僅保留 Moonshot；其餘中國雲已移除
    # Moonshot (CNY 官價以 7.2 換算)
    # ⚠ v5.12：kimi-k2.* 與 vision/auto 原本在 PROVIDER_DEFAULT_MODELS 被 seed 成可選模型，
    #   但 MODEL_PRICING 無對應價 → calc_cost 回 0 元（旗艦模型免費計費、漏收）。補齊如下。
    #   k2 價依 Moonshot 國際版官價估（input ~$0.6/M、output ~$2.5/M）；上線前請依實際合約校正。
    "kimi-k2.6":           (0.0006, 0.0025),
    "kimi-k2.5":           (0.0006, 0.0025),
    "moonshot-v1-8k":      (0.00167, 0.00167),
    "moonshot-v1-32k":     (0.00333, 0.00333),
    "moonshot-v1-128k":    (0.00833, 0.00833),
    "moonshot-v1-auto":    (0.00333, 0.00333),
    # Moonshot vision 模型吃圖+文、按 token 計（與同尺寸 v1 同價）
    "moonshot-v1-8k-vision-preview":   (0.00167, 0.00167),
    "moonshot-v1-32k-vision-preview":  (0.00333, 0.00333),
    "moonshot-v1-128k-vision-preview": (0.00833, 0.00833),
    # Groq
    "llama-3.1-70b-versatile": (0.00059, 0.00079),
    "llama-3.1-8b-instant":    (0.00005, 0.00008),
    "mixtral-8x7b-32768":      (0.00024, 0.00024),
    # Mistral
    "mistral-large-latest":    (0.002, 0.006),
    "mistral-small-latest":    (0.0002, 0.0006),
    # xAI
    "grok-beta":               (0.005, 0.015),
}


# v3.4 P1: non-LLM media pricing (USD)
# unit columns: image (per image) / second (per audio sec) / chars_1k (per 1k chars) / call (per call)
MEDIA_PRICING: dict[str, dict[str, float | None]] = {
    # OpenAI image gen
    "dall-e-3":              {"image": 0.04,  "second": None, "chars_1k": None, "call": None},
    "dall-e-3-hd":           {"image": 0.08,  "second": None, "chars_1k": None, "call": None},
    "dall-e-2":              {"image": 0.02,  "second": None, "chars_1k": None, "call": None},
    # OpenAI STT (Whisper) — $0.006/min = $0.0001/sec
    "whisper-1":             {"image": None,  "second": 0.0001, "chars_1k": None, "call": None},
    # OpenAI TTS — $15/1M chars = $0.015/1k; HD $30/1M
    "tts-1":                 {"image": None,  "second": None, "chars_1k": 0.015,  "call": None},
    "tts-1-hd":              {"image": None,  "second": None, "chars_1k": 0.030,  "call": None},
    # Reranker
    "bge-reranker-v2-m3":    {"image": None,  "second": None, "chars_1k": None, "call": 0},      # self-host free
    "rerank-multilingual-v3.0": {"image": None, "second": None, "chars_1k": None, "call": 0.001},  # cohere $1/1k calls
    "rerank-english-v3.0":   {"image": None,  "second": None, "chars_1k": None, "call": 0.001},
}

# v5.13：PROVIDER_DEFAULT_MODELS（寫死的「provider→預設模型清單」）已**移除**。
# 它過去被 agent 啟動 pricing_seed 拿去 INSERT model row，造成幻覺模型（gpt-4o 等）
# 在使用者刪掉後一重啟又復活。模型清單一律由 admin/models 即時動態偵測：
#   - ollama → /api/tags
#   - OpenAI 相容（含 Foundry / 類 OpenAI 自訂）→ /v1/models
# 計費仍走上面的 MODEL_PRICING / MEDIA_PRICING（只對既有 model row 補價，不造模型）。
