"""Chunking 公開 API。

使用方式：
    from app.core.chunking import get_chunker
    chunker = get_chunker("auto", chunk_size=512, chunk_overlap=64)
    chunks = chunker.split(text)
    for c in chunks:
        print(c.content, c.heading_path, c.chunk_type)
"""
from .auto import AutoChunker
from .base import Chunk
from .markdown import MarkdownChunker
from .qa import QaPairChunker
from .recursive import RecursiveChunker
from .tokens import approx_tokens

__all__ = [
    "Chunk", "approx_tokens",
    "AutoChunker", "MarkdownChunker", "QaPairChunker", "RecursiveChunker",
    "get_chunker", "AVAILABLE_STRATEGIES",
]

AVAILABLE_STRATEGIES = ("auto", "recursive", "markdown", "qa")


def get_chunker(
    strategy: str = "auto",
    chunk_size: int = 512,
    chunk_overlap: int = 64,
):
    """工廠：傳入策略名稱 + 參數，回傳對應 chunker 實例。"""
    s = (strategy or "auto").lower()
    if s == "auto":
        return AutoChunker(chunk_size, chunk_overlap)
    if s == "recursive":
        return RecursiveChunker(chunk_size, chunk_overlap)
    if s == "markdown":
        return MarkdownChunker(chunk_size, chunk_overlap)
    if s == "qa":
        return QaPairChunker(chunk_size * 2)
    raise ValueError(
        f"未知的切片策略：{strategy}；可用：{', '.join(AVAILABLE_STRATEGIES)}"
    )
