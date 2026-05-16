"""Media Provider Registry（M4 啟動）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Type

from .base import ImageProvider, STTProvider, TTSProvider
from .elevenlabs import ElevenLabsTTSProvider
from .openai import OpenAIImageProvider, OpenAISTTProvider, OpenAITTSProvider
from .stability import StabilityImageProvider


@dataclass
class MediaProviderMeta:
    type:             str
    label:            str
    capability:       str               # "image" | "tts" | "stt"
    default_base_url: str | None = None
    recommended_models: list[str] = field(default_factory=list)
    notes:            str = ""


MEDIA_PROVIDER_REGISTRY: list[MediaProviderMeta] = [
    # 圖像
    MediaProviderMeta("openai_image", "OpenAI Image (DALL-E)", "image",
                      default_base_url="https://api.openai.com/v1",
                      recommended_models=["dall-e-3", "gpt-image-1"]),
    MediaProviderMeta("stability_image", "Stability AI", "image",
                      default_base_url="https://api.stability.ai",
                      recommended_models=["core", "sd3.5-large", "ultra"]),
    # TTS
    MediaProviderMeta("openai_tts", "OpenAI TTS", "tts",
                      default_base_url="https://api.openai.com/v1",
                      recommended_models=["tts-1", "tts-1-hd", "gpt-4o-mini-tts"]),
    MediaProviderMeta("elevenlabs_tts", "ElevenLabs", "tts",
                      default_base_url="https://api.elevenlabs.io",
                      recommended_models=["eleven_multilingual_v2", "eleven_turbo_v2_5"]),
    # STT
    MediaProviderMeta("openai_stt", "OpenAI STT (Whisper)", "stt",
                      default_base_url="https://api.openai.com/v1",
                      recommended_models=["whisper-1", "gpt-4o-transcribe"]),
]


_IMAGE_TABLE: dict[str, Type[ImageProvider]] = {
    "openai_image":    OpenAIImageProvider,
    "stability_image": StabilityImageProvider,
}
_TTS_TABLE: dict[str, Type[TTSProvider]] = {
    "openai_tts":     OpenAITTSProvider,
    "elevenlabs_tts": ElevenLabsTTSProvider,
}
_STT_TABLE: dict[str, Type[STTProvider]] = {
    "openai_stt": OpenAISTTProvider,
}


def get_image_provider(provider_type: str) -> Type[ImageProvider]:
    return _IMAGE_TABLE.get(provider_type, OpenAIImageProvider)


def get_tts_provider(provider_type: str) -> Type[TTSProvider]:
    return _TTS_TABLE.get(provider_type, OpenAITTSProvider)


def get_stt_provider(provider_type: str) -> Type[STTProvider]:
    return _STT_TABLE.get(provider_type, OpenAISTTProvider)
