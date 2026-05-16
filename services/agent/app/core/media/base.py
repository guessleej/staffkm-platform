"""Media Provider 抽象基底（M4 啟動）。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ImageResult:
    """圖像生成結果：URL 或 base64 二擇一。"""
    url:            str | None = None
    b64_json:       str | None = None
    revised_prompt: str | None = None
    raw:            dict[str, Any] | None = None


class ImageProvider(ABC):
    provider_type: str = ""

    def __init__(self, api_key: str | None, base_url: str | None = None, config: dict[str, Any] | None = None) -> None:
        self.api_key  = api_key
        self.base_url = base_url
        self.config   = config or {}

    @abstractmethod
    async def generate(
        self, *, prompt: str, model: str, size: str = "1024x1024",
        n: int = 1, output_type: str = "url",
        extra: dict[str, Any] | None = None,
    ) -> list[ImageResult]:
        ...


class TTSProvider(ABC):
    provider_type: str = ""

    def __init__(self, api_key: str | None, base_url: str | None = None, config: dict[str, Any] | None = None) -> None:
        self.api_key  = api_key
        self.base_url = base_url
        self.config   = config or {}

    @abstractmethod
    async def synthesize(
        self, *, text: str, voice: str, model: str,
        speed: float = 1.0, output_format: str = "mp3",
    ) -> bytes:
        ...


class STTProvider(ABC):
    provider_type: str = ""

    def __init__(self, api_key: str | None, base_url: str | None = None, config: dict[str, Any] | None = None) -> None:
        self.api_key  = api_key
        self.base_url = base_url
        self.config   = config or {}

    @abstractmethod
    async def transcribe(
        self, *, audio_bytes: bytes, model: str,
        filename: str = "audio.mp3", language: str | None = None,
    ) -> str:
        ...
