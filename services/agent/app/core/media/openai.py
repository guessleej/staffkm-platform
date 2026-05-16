"""OpenAI media adapters（封裝既有 _exec_image/stt/tts 行為）。"""
from __future__ import annotations

from typing import Any

import httpx
from openai import AsyncOpenAI

from .base import ImageProvider, ImageResult, STTProvider, TTSProvider


class OpenAIImageProvider(ImageProvider):
    provider_type = "openai_image"

    def __init__(self, api_key, base_url=None, config=None):
        super().__init__(api_key, base_url, config)
        kw: dict[str, Any] = {"api_key": api_key or "sk-not-needed"}
        if base_url:
            kw["base_url"] = base_url
        self._client = AsyncOpenAI(**kw)

    async def generate(
        self, *, prompt, model="dall-e-3", size="1024x1024",
        n=1, output_type="url", extra=None,
    ):
        kwargs: dict[str, Any] = {
            "model": model, "prompt": prompt, "n": n, "size": size,
            "response_format": "b64_json" if output_type == "base64" else "url",
        }
        kwargs.update(extra or {})
        resp = await self._client.images.generate(**kwargs)
        out: list[ImageResult] = []
        for d in resp.data or []:
            out.append(ImageResult(
                url=getattr(d, "url", None),
                b64_json=getattr(d, "b64_json", None),
                revised_prompt=getattr(d, "revised_prompt", None),
            ))
        return out


class OpenAITTSProvider(TTSProvider):
    provider_type = "openai_tts"

    async def synthesize(self, *, text, voice="alloy", model="tts-1", speed=1.0, output_format="mp3"):
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        base = (self.base_url or "https://api.openai.com/v1").rstrip("/")
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(
                f"{base}/audio/speech", headers=headers,
                json={
                    "model": model, "input": text, "voice": voice,
                    "speed": speed, "response_format": output_format,
                },
            )
            r.raise_for_status()
            return r.content


class OpenAISTTProvider(STTProvider):
    provider_type = "openai_stt"

    async def transcribe(self, *, audio_bytes, model="whisper-1", filename="audio.mp3", language=None):
        headers: dict[str, str] = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        base = (self.base_url or "https://api.openai.com/v1").rstrip("/")
        form: dict[str, Any] = {"model": model}
        if language:
            form["language"] = language
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(
                f"{base}/audio/transcriptions", headers=headers,
                files={"file": (filename, audio_bytes, "audio/mpeg")}, data=form,
            )
            r.raise_for_status()
            return r.json().get("text", "")
