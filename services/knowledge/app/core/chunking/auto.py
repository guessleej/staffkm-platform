"""AutoChunker — 依內容啟發式偵測，挑選最合適的切片策略。

判斷規則（原創實作，輕量啟發式）：
  1. 偵測到 markdown heading（^#{1,6} ）密度 ≥ 0.5%（行數比例）→ markdown
  2. 偵測到 QA marker（Q:/A:/問:/答:）數量 ≥ 4 → qa
  3. 否則 → recursive
"""
from __future__ import annotations

import re

from .base import Chunk
from .markdown import MarkdownChunker
from .qa import QaPairChunker
from .recursive import RecursiveChunker


_HEADING_RE = re.compile(r"^#{1,6}\s+\S", re.MULTILINE)
_QA_RE      = re.compile(r"^\s*(?:[QqAa問答]|問題|回答)[\s：:.、\-]+", re.MULTILINE)


class AutoChunker:
    name = "auto"

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def detect_strategy(self, text: str) -> str:
        lines = text.count("\n") + 1
        heading_count = len(_HEADING_RE.findall(text))
        qa_count = len(_QA_RE.findall(text))

        # Markdown 啟發式：heading 與行數比例
        if lines > 0 and heading_count / max(lines, 1) >= 0.005 and heading_count >= 2:
            return "markdown"
        if qa_count >= 4:
            return "qa"
        return "recursive"

    def split(self, text: str) -> list[Chunk]:
        strategy = self.detect_strategy(text)
        if strategy == "markdown":
            return MarkdownChunker(self.chunk_size, self.chunk_overlap).split(text)
        if strategy == "qa":
            out = QaPairChunker(self.chunk_size * 2).split(text)
            if out:
                return out
            # QA 偵測雖中但沒找到 marker 邊界 → fallback
        return RecursiveChunker(self.chunk_size, self.chunk_overlap).split(text)
