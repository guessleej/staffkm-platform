"""ElevenLabs TTS adapter（M4 啟動 — scaffold）。

走 v1 REST：
  POST /v1/text-to-speech/{voice_id}
  Header: xi-api-key: {api_key}
"""
from __future__ import annotations

import httpx

from .base import TTSProvider


class ElevenLabsTTSProvider(TTSProvider):
    provider_type = "elevenlabs_tts"

    DEFAULT_BASE = "https://api.elevenlabs.io"

    def __init__(self, api_key, base_url=None, config=None):
        super().__init__(api_key, base_url or self.DEFAULT_BASE, config)
        self._client = httpx.AsyncClient(timeout=120.0)

    async def synthesize(
        self, *, text, voice="EXAVITQu4vr4xnSDxMaL",
        model="eleven_multilingual_v2", speed=1.0, output_format="mp3",
    ):
        # ElevenLabs voice 欄位是 voice_id；speed 透過 voice_settings.style 不支援，
        # 此處保持 API 表面，speed 留待 future PR 走他們的 speech_rate（v2）擴充
        headers = {
            "xi-api-key":   self.api_key or "",
            "Content-Type": "application/json",
            "Accept":       "audio/mpeg",
        }
        body = {
            "text":     text,
            "model_id": model,
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        }
        r = await self._client.post(
            f"{self.base_url}/v1/text-to-speech/{voice}",
            headers=headers, json=body,
        )
        r.raise_for_status()
        return r.content
