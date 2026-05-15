"""Embedding 服務 — 支援 OpenAI / HuggingFace TEI / 任意 OpenAI-compatible endpoint"""
from functools import lru_cache

import structlog

log = structlog.get_logger()


# E5 系列模型必須加 prefix（漏掉品質會掉 10%+）
# 參考 https://huggingface.co/intfloat/multilingual-e5-large
_E5_FAMILIES = ("e5-",)


def _is_e5(model: str) -> bool:
    name = model.lower()
    return any(fam in name for fam in _E5_FAMILIES)


class EmbeddingService:
    def __init__(self, model: str, api_key: str, base_url: str | None = None):
        self.model = model
        self.api_key = api_key or "dummy"  # TEI 不需 key 但 OpenAI client 必填
        self.base_url = base_url
        self._client = None
        self._needs_e5_prefix = _is_e5(model)

    def _get_client(self):
        if self._client is None:
            from openai import AsyncOpenAI
            kwargs: dict = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = AsyncOpenAI(**kwargs)
        return self._client

    def _format_query(self, text: str) -> str:
        """E5 model：query 端要前綴 'query: '。"""
        if self._needs_e5_prefix and not text.startswith(("query:", "passage:")):
            return f"query: {text}"
        return text

    def _format_passage(self, text: str) -> str:
        """E5 model：document 端要前綴 'passage: '。"""
        if self._needs_e5_prefix and not text.startswith(("query:", "passage:")):
            return f"passage: {text}"
        return text

    async def embed_query(self, text: str) -> list[float]:
        """檢索時呼叫，會自動加 query: 前綴。"""
        client = self._get_client()
        resp = await client.embeddings.create(
            input=self._format_query(text), model=self.model,
        )
        return resp.data[0].embedding

    async def embed_text(self, text: str) -> list[float]:
        """向後相容別名 — 視為 query。"""
        return await self.embed_query(text)

    async def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """文件入庫批次向量化，自動加 passage: 前綴。"""
        results: list[list[float]] = []
        client = self._get_client()
        for i in range(0, len(texts), batch_size):
            batch = [self._format_passage(t) for t in texts[i: i + batch_size]]
            resp = await client.embeddings.create(input=batch, model=self.model)
            results.extend([item.embedding for item in sorted(resp.data, key=lambda x: x.index)])
        return results


@lru_cache
def get_embedder(model: str, api_key: str, base_url: str | None = None) -> EmbeddingService:
    return EmbeddingService(model=model, api_key=api_key, base_url=base_url)
