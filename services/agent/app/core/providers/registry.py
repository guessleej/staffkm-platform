"""Provider Registry — 30+ provider 的中繼資料。

每筆紀錄包含：
- type            字串 ID（DB model_providers.provider_type 對應）
- label           顯示名稱
- adapter_type    走哪個 adapter
- default_base_url
- recommended_models  常見可用 model id
- needs_api_key
- notes           中文備註
- capabilities    v5.0.6: LLM / Embedding / Reranker / TTS / STT / Vision / Image / Moderation
- is_local        v5.0.6: 地端 self-host (右側 catalog 加「地端」chip)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Type

from .anthropic import AnthropicProvider
from .base import BaseProvider
from .bedrock import BedrockProvider
from .cohere import CohereProvider
from .gemini import GeminiProvider
from .minimax import MiniMaxProvider
from .openai_compat import OpenAICompatProvider
from .vertex_ai import VertexAIProvider


@dataclass
class ProviderMeta:
    type:                str
    label:               str
    adapter_type:        str
    default_base_url:    str | None = None
    recommended_models:  list[str]  = field(default_factory=list)
    needs_api_key:       bool       = True
    notes:               str        = ""
    capabilities:        list[str]  = field(default_factory=lambda: ["LLM"])
    is_local:            bool       = False


# ── 30+ providers ──────────────────────────────────────────────────────
PROVIDER_REGISTRY: list[ProviderMeta] = [
    # ════════════════════════════════════════════════════════════════════
    # 1) 地端 LLM serving framework
    # ════════════════════════════════════════════════════════════════════
    # Docker Desktop（Mac/Win）連 host 機 ollama 用 host.docker.internal；
    # verify 走原生 /api/tags，base_url 不可帶 /v1（帶了會變 /v1/api/tags → 404）。
    # 若 ollama 跑在 compose 內請改成該服務名（本專案地端 embedding 容器叫 embedder）。
    ProviderMeta("ollama", "Ollama", "openai_compat",
                 default_base_url="http://host.docker.internal:11434",
                 recommended_models=[],  # 不寫死；建立後由 /api/tags 即時同步真實模型
                 needs_api_key=False, is_local=True,
                 capabilities=["LLM", "Embedding", "Vision"],
                 notes="最易上手地端 serving；模型清單由伺服器 /api/tags 自動同步，不需手動填。"),
    ProviderMeta("llama_cpp", "llama.cpp (llama-server)", "openai_compat",
                 default_base_url="http://llama-server:8080/v1",
                 recommended_models=["Llama-3.1-8B-Q4_K_M.gguf"],
                 needs_api_key=False, is_local=True,
                 capabilities=["LLM", "Embedding"],
                 notes="GGUF 格式直跑；CPU/Metal/CUDA 友善；--api-mode 開 OpenAI compat。"),
    ProviderMeta("vllm", "vLLM", "openai_compat",
                 default_base_url="http://vllm:8000/v1",
                 recommended_models=["meta-llama/Meta-Llama-3.1-8B-Instruct", "Qwen/Qwen2.5-7B-Instruct"],
                 needs_api_key=False, is_local=True,
                 capabilities=["LLM"],
                 notes="高 throughput PagedAttention；多 GPU/TP；production 首選。"),
    ProviderMeta("sglang", "SGLang", "openai_compat",
                 default_base_url="http://sglang:30000/v1",
                 recommended_models=["meta-llama/Meta-Llama-3.1-8B-Instruct"],
                 needs_api_key=False, is_local=True,
                 capabilities=["LLM"],
                 notes="RadixAttention 對 batch / structured output 強；low-latency 場景。"),
    ProviderMeta("tgi", "Hugging Face TGI", "openai_compat",
                 default_base_url="http://tgi:80/v1",
                 needs_api_key=False, is_local=True,
                 capabilities=["LLM"],
                 notes="Text Generation Inference；HF 官方，FlashAttention + 量化。"),
    ProviderMeta("lmstudio", "LM Studio", "openai_compat",
                 default_base_url="http://host.docker.internal:1234/v1",
                 recommended_models=["lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF"],
                 needs_api_key=False, is_local=True,
                 capabilities=["LLM", "Embedding"],
                 notes="桌機 GUI；Mac 上跑模型最簡單；REST server 預設 1234。"),
    ProviderMeta("xinference", "Xinference", "openai_compat",
                 default_base_url="http://xinference:9997/v1",
                 needs_api_key=False, is_local=True,
                 capabilities=["LLM", "Embedding", "Reranker", "STT", "TTS", "Image"],
                 notes="Xorbits 出品；單一 endpoint 跑 LLM / embedding / rerank / 音訊 / 圖像。"),
    ProviderMeta("localai", "LocalAI", "openai_compat",
                 default_base_url="http://localai:8080/v1",
                 needs_api_key=False, is_local=True,
                 capabilities=["LLM", "Embedding", "Image", "STT", "TTS"],
                 notes="多後端 (llama.cpp / whisper / stable-diffusion)；OpenAI drop-in。"),
    ProviderMeta("text_gen_webui", "Text Generation WebUI", "openai_compat",
                 default_base_url="http://text-gen-webui:5000/v1",
                 needs_api_key=False, is_local=True,
                 capabilities=["LLM"],
                 notes="oobabooga；GUI + REST，支援多種 backend。"),
    ProviderMeta("gpt4all", "GPT4All", "openai_compat",
                 default_base_url="http://host.docker.internal:4891/v1",
                 needs_api_key=False, is_local=True,
                 capabilities=["LLM"],
                 notes="Nomic AI；桌機 GUI；low-end PC 友善。"),

    # ════════════════════════════════════════════════════════════════════
    # 2) 國際雲端 LLM
    # ════════════════════════════════════════════════════════════════════
    ProviderMeta("openai", "OpenAI", "openai_compat",
                 default_base_url="https://api.openai.com/v1",
                 recommended_models=["gpt-4o-mini", "gpt-4o", "o4-mini", "text-embedding-3-small", "dall-e-3", "whisper-1", "tts-1"],
                 capabilities=["LLM", "Embedding", "Vision", "Image", "STT", "TTS", "Moderation"]),
    ProviderMeta("azure_openai", "Azure OpenAI", "openai_compat",
                 capabilities=["LLM", "Embedding", "Vision", "Image", "STT", "TTS"],
                 notes="base_url 形如 https://{resource}.openai.azure.com/openai/deployments/{deployment}"),
    ProviderMeta("anthropic", "Anthropic Claude", "anthropic",
                 default_base_url="https://api.anthropic.com",
                 recommended_models=["claude-opus-4-5", "claude-sonnet-4-5", "claude-haiku-4-5"],
                 capabilities=["LLM", "Vision"],
                 notes="走 messages API；system 自動拆成頂層欄位。"),
    ProviderMeta("bedrock", "AWS Bedrock", "bedrock",
                 capabilities=["LLM", "Embedding", "Image"],
                 notes="走 aioboto3 + SigV4；目前支援 Claude on Bedrock。需在部署環境安裝 aioboto3。"),
    ProviderMeta("gemini", "Google Gemini", "gemini",
                 default_base_url="https://generativelanguage.googleapis.com",
                 recommended_models=["gemini-2.5-pro", "gemini-2.5-flash"],
                 capabilities=["LLM", "Embedding", "Vision"],
                 notes="走 generateContent REST + API key；system 自動轉 systemInstruction。"),
    ProviderMeta("vertex_ai", "Google Vertex AI", "vertex_ai",
                 recommended_models=["gemini-2.5-pro", "gemini-2.5-flash"],
                 capabilities=["LLM", "Embedding", "Vision", "Image"],
                 notes="走 GCP aiplatform REST + Bearer access_token；config 須帶 region / project_id。"),
    ProviderMeta("cohere", "Cohere", "cohere",
                 default_base_url="https://api.cohere.com",
                 recommended_models=["command-r-plus", "command-r", "rerank-multilingual-v3.0"],
                 capabilities=["LLM", "Embedding", "Reranker"],
                 notes="走 Cohere v2 chat REST + Bearer token；reranker 也走它。"),
    ProviderMeta("mistral", "Mistral AI", "openai_compat",
                 default_base_url="https://api.mistral.ai/v1",
                 recommended_models=["mistral-large-latest", "mistral-small-latest"],
                 capabilities=["LLM", "Embedding"]),
    ProviderMeta("groq", "Groq", "openai_compat",
                 default_base_url="https://api.groq.com/openai/v1",
                 recommended_models=["llama-3.1-70b-versatile", "mixtral-8x7b-32768"],
                 capabilities=["LLM"],
                 notes="LPU 加速；推論速度業界最快。"),
    ProviderMeta("together", "Together AI", "openai_compat",
                 default_base_url="https://api.together.xyz/v1",
                 capabilities=["LLM", "Embedding", "Image"]),
    ProviderMeta("fireworks", "Fireworks AI", "openai_compat",
                 default_base_url="https://api.fireworks.ai/inference/v1",
                 recommended_models=["accounts/fireworks/models/llama-v3p1-70b-instruct"],
                 capabilities=["LLM", "Embedding", "Image"]),
    ProviderMeta("perplexity", "Perplexity", "openai_compat",
                 default_base_url="https://api.perplexity.ai",
                 capabilities=["LLM"]),
    ProviderMeta("openrouter", "OpenRouter", "openai_compat",
                 default_base_url="https://openrouter.ai/api/v1",
                 capabilities=["LLM"],
                 notes="統一接 300+ 模型的路由服務。"),
    ProviderMeta("xai", "xAI (Grok)", "openai_compat",
                 default_base_url="https://api.x.ai/v1",
                 recommended_models=["grok-2-latest", "grok-2-vision-latest"],
                 capabilities=["LLM", "Vision"]),
    ProviderMeta("nvidia_nim", "NVIDIA NIM", "openai_compat",
                 default_base_url="https://integrate.api.nvidia.com/v1",
                 capabilities=["LLM", "Embedding", "Reranker"],
                 notes="NVIDIA 雲端 inference; 也可本地起 NIM container。"),

    # ════════════════════════════════════════════════════════════════════
    # 3) 中文 / 亞洲雲端
    # v5.7: 僅保留 Moonshot (Kimi)，其餘中國雲（DeepSeek/Zhipu/Qwen/Baichuan/
    # MiniMax/SiliconFlow/Yi/Doubao/Hunyuan/Qianfan/Bailian）已移除
    # ════════════════════════════════════════════════════════════════════
    ProviderMeta("moonshot", "Moonshot (Kimi)", "openai_compat",
                 default_base_url="https://api.moonshot.ai/v1",
                 recommended_models=["kimi-k2.6", "kimi-k2.5", "moonshot-v1-128k", "moonshot-v1-32k", "moonshot-v1-8k"],
                 capabilities=["LLM", "Vision"],
                 notes="國際版預設 (.ai)；中國平台請改 base_url 成 https://api.moonshot.cn/v1。"),

    # ════════════════════════════════════════════════════════════════════
    # 4) Specialty (專門 capability)
    # ════════════════════════════════════════════════════════════════════
    ProviderMeta("voyage", "Voyage AI", "openai_compat",
                 default_base_url="https://api.voyageai.com/v1",
                 recommended_models=["voyage-3", "rerank-2"],
                 capabilities=["Embedding", "Reranker"],
                 notes="專做高品質 embedding + reranker (Anthropic 推薦)。"),
    ProviderMeta("jina", "Jina AI", "openai_compat",
                 default_base_url="https://api.jina.ai/v1",
                 recommended_models=["jina-embeddings-v3", "jina-reranker-v2-base-multilingual"],
                 capabilities=["Embedding", "Reranker"]),
    ProviderMeta("elevenlabs", "ElevenLabs", "openai_compat",
                 default_base_url="https://api.elevenlabs.io/v1",
                 capabilities=["TTS", "STT"],
                 notes="高品質 TTS / 多語音複製。"),
    ProviderMeta("deepgram", "Deepgram", "openai_compat",
                 default_base_url="https://api.deepgram.com/v1",
                 capabilities=["STT"],
                 notes="專業 STT / live transcription。"),
    ProviderMeta("stability_ai", "Stability AI", "openai_compat",
                 default_base_url="https://api.stability.ai/v2beta",
                 capabilities=["Image"],
                 notes="Stable Diffusion 系列 image generation。"),
]


# adapter_type → class 對應
_ADAPTER_TABLE: dict[str, Type[BaseProvider]] = {
    "openai_compat": OpenAICompatProvider,
    "anthropic":  AnthropicProvider,
    "gemini":     GeminiProvider,
    "cohere":     CohereProvider,
    "bedrock":    BedrockProvider,
    "vertex_ai":  VertexAIProvider,
    "minimax":    MiniMaxProvider,
}


def get_adapter(provider_type: str) -> Type[BaseProvider]:
    for meta in PROVIDER_REGISTRY:
        if meta.type == provider_type:
            return _ADAPTER_TABLE.get(meta.adapter_type, OpenAICompatProvider)
    return OpenAICompatProvider


def list_providers() -> list[dict]:
    """給 API/前端用，回傳 JSON-friendly dict 清單。"""
    return [
        {
            "type":               m.type,
            "label":              m.label,
            "adapter_type":       m.adapter_type,
            "default_base_url":   m.default_base_url,
            "recommended_models": m.recommended_models,
            "needs_api_key":      m.needs_api_key,
            "notes":              m.notes,
            "capabilities":       m.capabilities,
            "is_local":           m.is_local,
        }
        for m in PROVIDER_REGISTRY
    ]
