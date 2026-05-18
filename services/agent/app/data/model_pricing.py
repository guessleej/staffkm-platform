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
    # Ollama / self-hosted
    "llama3.1":            (0, 0),
    "llama3.2":            (0, 0),
    "qwen2.5":             (0, 0),
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
