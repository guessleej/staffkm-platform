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
    # v5.7 — 僅保留 Moonshot；其餘中國雲已移除
    # Moonshot (CNY 官價以 7.2 換算)
    "moonshot-v1-8k":      (0.00167, 0.00167),
    "moonshot-v1-32k":     (0.00333, 0.00333),
    "moonshot-v1-128k":    (0.00833, 0.00833),
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

# v5.0.4: provider_type → 預設 model rows（INSERT 進 ai_models 給 admin UI 顯示）
# (model_name, model_type, display_name)
PROVIDER_DEFAULT_MODELS: dict[str, list[tuple[str, str, str]]] = {
    "openai": [
        ("gpt-4o",                  "llm",       "GPT-4o"),
        ("gpt-4o-mini",             "llm",       "GPT-4o mini"),
        ("gpt-4-turbo",             "llm",       "GPT-4 Turbo"),
        ("gpt-3.5-turbo",           "llm",       "GPT-3.5 Turbo"),
        ("o1-preview",              "llm",       "o1-preview"),
        ("o1-mini",                 "llm",       "o1-mini"),
        ("text-embedding-3-small",  "embedding", "Embedding 3 small"),
        ("text-embedding-3-large",  "embedding", "Embedding 3 large"),
        ("dall-e-3",                "image",     "DALL·E 3"),
        ("dall-e-3-hd",             "image",     "DALL·E 3 HD"),
        ("whisper-1",               "stt",       "Whisper"),
        ("tts-1",                   "tts",       "TTS-1"),
        ("tts-1-hd",                "tts",       "TTS-1 HD"),
    ],
    "anthropic": [
        ("claude-3-5-sonnet-20241022", "llm", "Claude 3.5 Sonnet"),
        ("claude-3-5-haiku-20241022",  "llm", "Claude 3.5 Haiku"),
        ("claude-3-opus-20240229",     "llm", "Claude 3 Opus"),
    ],
    "google": [
        ("gemini-1.5-pro",   "llm", "Gemini 1.5 Pro"),
        ("gemini-1.5-flash", "llm", "Gemini 1.5 Flash"),
    ],
    "ollama": [
        ("llama3.1",           "llm",       "Llama 3.1"),
        ("llama3.2",           "llm",       "Llama 3.2"),
        ("qwen2.5",            "llm",       "Qwen 2.5"),
        ("bge-m3",             "embedding", "BGE-M3 embedding"),
        ("bge-reranker-v2-m3", "reranker",  "BGE Reranker v2 M3"),
    ],
    # v5.0.6: 地端 serving framework
    "llama_cpp": [
        ("Llama-3.1-8B-Q4_K_M.gguf", "llm", "Llama 3.1 8B (Q4_K_M)"),
    ],
    "vllm": [
        ("meta-llama/Meta-Llama-3.1-8B-Instruct", "llm", "Llama 3.1 8B Instruct"),
        ("Qwen/Qwen2.5-7B-Instruct",              "llm", "Qwen 2.5 7B Instruct"),
    ],
    "sglang": [
        ("meta-llama/Meta-Llama-3.1-8B-Instruct", "llm", "Llama 3.1 8B Instruct"),
    ],
    "tgi": [
        ("meta-llama/Meta-Llama-3.1-8B-Instruct", "llm", "Llama 3.1 8B Instruct"),
    ],
    "lmstudio": [
        ("lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF", "llm", "Llama 3.1 8B (LM Studio)"),
    ],
    "xinference": [
        ("qwen2.5-instruct",   "llm",       "Qwen 2.5 Instruct"),
        ("bge-m3",             "embedding", "BGE-M3"),
        ("bge-reranker-v2-m3", "reranker",  "BGE Reranker v2 M3"),
    ],
    "localai": [
        ("gpt-4",  "llm",       "LocalAI gpt-4 alias"),
        ("bge-m3", "embedding", "BGE-M3"),
    ],
    "cohere": [
        ("rerank-multilingual-v3.0", "reranker", "Cohere Rerank v3 multilingual"),
        ("rerank-english-v3.0",      "reranker", "Cohere Rerank v3 English"),
    ],
    # v5.0.15: 中國 / 國際 cloud LLM（openai_compat 系，registry 已註冊但漏 seed）
    # v5.7: 中國雲只保留 Moonshot；其餘中國 / 非主流雲已移除
    "moonshot": [
        ("moonshot-v1-8k",   "llm", "Moonshot v1 8K"),
        ("moonshot-v1-32k",  "llm", "Moonshot v1 32K"),
        ("moonshot-v1-128k", "llm", "Moonshot v1 128K"),
    ],
    "groq": [
        ("llama-3.1-70b-versatile", "llm", "Llama 3.1 70B (Groq)"),
        ("llama-3.1-8b-instant",    "llm", "Llama 3.1 8B (Groq)"),
        ("mixtral-8x7b-32768",      "llm", "Mixtral 8x7B (Groq)"),
    ],
    "together": [
        ("meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo", "llm", "Llama 3.1 70B Turbo"),
    ],
    "mistral": [
        ("mistral-large-latest", "llm", "Mistral Large"),
        ("mistral-small-latest", "llm", "Mistral Small"),
    ],
    "perplexity": [
        ("llama-3.1-sonar-large-128k-online", "llm", "Sonar Large (online)"),
        ("llama-3.1-sonar-small-128k-online", "llm", "Sonar Small (online)"),
    ],
    "openrouter": [
        ("openai/gpt-4o",                         "llm", "GPT-4o (via OpenRouter)"),
        ("anthropic/claude-3.5-sonnet",           "llm", "Claude 3.5 Sonnet (via OpenRouter)"),
        ("meta-llama/llama-3.1-70b-instruct",     "llm", "Llama 3.1 70B (via OpenRouter)"),
    ],
    "xai": [
        ("grok-beta", "llm", "Grok Beta"),
    ],
    "fireworks": [
        ("accounts/fireworks/models/llama-v3p1-70b-instruct", "llm", "Llama 3.1 70B (Fireworks)"),
    ],
    "azure_openai": [
        ("gpt-4o",      "llm", "Azure GPT-4o"),
        ("gpt-4o-mini", "llm", "Azure GPT-4o mini"),
    ],
    "nvidia_nim": [
        ("meta/llama-3.1-70b-instruct", "llm", "Llama 3.1 70B (NIM)"),
    ],
}
