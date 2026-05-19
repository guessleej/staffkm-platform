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

# v2.8.1：偵測 strategy 前先把 ``` code fence 內的內容剝掉，
# 避免程式碼註解（# foo / ## bar）被誤判為 markdown heading。
_FENCE_BLOCK_RE = re.compile(r"^[ \t]*```.*?(?:\n[ \t]*```|\Z)", re.MULTILINE | re.DOTALL)


def _strip_code_fences(text: str) -> str:
    """以「state machine 等價」的方式移除整段 fenced code block。
    遇到 EOF 仍未閉合 → 截到結尾為止。"""
    return _FENCE_BLOCK_RE.sub("", text)


class AutoChunker:
    name = "auto"

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def detect_strategy(self, text: str) -> str:
        # v2.8.1：先剝掉 fenced code block 再計算 heading / QA marker
        # （程式碼註解 # foo / Q: print(x) 等不應影響 strategy 判斷）
        scan = _strip_code_fences(text)
        lines = scan.count("\n") + 1
        heading_count = len(_HEADING_RE.findall(scan))
        qa_count = len(_QA_RE.findall(scan))

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
