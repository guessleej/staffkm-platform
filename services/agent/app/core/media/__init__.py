"""Media Provider 抽象介面（M4 啟動）。

對標 core/providers（文字 LLM），但聚焦圖像 / 語音：
- ImageProvider：generate(prompt) -> ImageResult  /  understand(image) -> str
- TTSProvider:   synthesize(text) -> bytes
- STTProvider:   transcribe(audio_bytes) -> str

目前提供：
- OpenAIImageProvider（DALL-E 3 / gpt-image-1）
- OpenAITTSProvider / OpenAISTTProvider（whisper / tts-1）
- StabilityImageProvider（scaffold；走 Stability AI v2beta）
- ElevenLabsTTSProvider（scaffold；走 v1 text-to-speech）

未涵蓋：影片生成、即時對話語音（Realtime API）。
"""
from .base import (
    ImageProvider, ImageResult, STTProvider, TTSProvider,
)
from .openai import (
    OpenAIImageProvider, OpenAISTTProvider, OpenAITTSProvider,
)
from .stability import StabilityImageProvider
from .elevenlabs import ElevenLabsTTSProvider
from .registry import (
    MEDIA_PROVIDER_REGISTRY, MediaProviderMeta,
    get_image_provider, get_stt_provider, get_tts_provider,
)

__all__ = [
    "ImageProvider", "ImageResult",
    "TTSProvider", "STTProvider",
    "OpenAIImageProvider", "OpenAITTSProvider", "OpenAISTTProvider",
    "StabilityImageProvider", "ElevenLabsTTSProvider",
    "MEDIA_PROVIDER_REGISTRY", "MediaProviderMeta",
    "get_image_provider", "get_tts_provider", "get_stt_provider",
]
