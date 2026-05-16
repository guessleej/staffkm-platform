"""QA-pair 切片器 — 偵測「問題 / 回答」格式，每組為一個 chunk。

適用場景：
  - FAQ 文件（Q: ... A: ...）
  - 客服紀錄
  - 條列式問答

啟發式偵測規則（原創實作）：
  - 以正規表式抓「(Q|問|問題)[：:]?」或「(A|答|回答)[：:]?」開頭
  - 連續 Q-A 視為同一組
  - 若整個文件都找不到任何 QA marker → 回傳空 list（呼叫端 fallback）
"""
from __future__ import annotations

import re

from .base import Chunk


_QA_HEAD_RE = re.compile(
    r"^\s*(?:[QqAa問答]|問題|回答|題目|解答)[\s：:.、\-]+",
    re.MULTILINE,
)


class QaPairChunker:
    name = "qa"

    def __init__(self, chunk_size: int = 1024):
        # qa chunk 通常較長，但仍設上限避免巨型 QA 灌爆 embedding
        self.chunk_size = chunk_size

    def split(self, text: str) -> list[Chunk]:
        if not text.strip():
            return []

        # 找所有 QA marker 的起始位置
        markers = list(_QA_HEAD_RE.finditer(text))
        if not markers:
            return []  # 沒偵測到 QA 格式 → 呼叫端 fallback

        chunks: list[Chunk] = []
        # 每個 marker 起點到下一個 marker 起點為一段
        for i, m in enumerate(markers):
            start = m.start()
            end = markers[i + 1].start() if i + 1 < len(markers) else len(text)
            piece = text[start:end].strip()
            if not piece:
                continue
            # 若 piece 過長 → 截斷（保留前半 + 標註）
            if len(piece) > self.chunk_size:
                piece = piece[: self.chunk_size].rstrip() + " …"
            chunks.append(Chunk(
                content=piece,
                char_start=start,
                char_end=end,
                chunk_type="qa",
            ))
        return chunks
