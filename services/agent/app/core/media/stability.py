"""Stability AI Image adapter（M4 啟動 — scaffold）。

走 v2beta REST：
  POST https://api.stability.ai/v2beta/stable-image/generate/{model}
"""
from __future__ import annotations

import base64
from typing import Any

import httpx

from .base import ImageProvider, ImageResult


class StabilityImageProvider(ImageProvider):
    provider_type = "stability_image"

    DEFAULT_BASE = "https://api.stability.ai"

    def __init__(self, api_key, base_url=None, config=None):
        super().__init__(api_key, base_url or self.DEFAULT_BASE, config)
        self._client = httpx.AsyncClient(timeout=120.0)

    async def generate(
        self, *, prompt, model="core", size="1024x1024",
        n=1, output_type="base64", extra=None,
    ):
        # Stability v2beta 接 multipart；output_format 預設 png；尺寸交給 aspect_ratio
        # size 簡化：寬高相等以 "1:1"，矩形請改 ratio 字串透過 extra 傳
        ar = (extra or {}).get("aspect_ratio") or "1:1"
        form: dict[str, Any] = {
            "prompt":        prompt,
            "aspect_ratio":  ar,
            "output_format": "png",
        }
        for k, v in (extra or {}).items():
            if k not in form:
                form[k] = v

        headers = {
            "Authorization": f"Bearer {self.api_key or ''}",
            "Accept":        "image/*",
        }
        r = await self._client.post(
            f"{self.base_url}/v2beta/stable-image/generate/{model}",
            headers=headers, files={"none": ("", "")}, data=form,
        )
        r.raise_for_status()
        # 回傳的是 binary image bytes；統一封成 base64
        b64 = base64.b64encode(r.content).decode()
        return [ImageResult(b64_json=b64)]
