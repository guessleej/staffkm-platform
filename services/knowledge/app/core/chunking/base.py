"""Chunking base：通用 Chunk 結構與切片器介面。

設計目標（RAG best-practice，原創實作）：
  - 每個 chunk 不只是純文字，還帶 metadata（heading path / 來源段落 /
    char_start / char_end / chunk type）→ 利後續 citation / rerank
  - 切片器一律遵循 Protocol，可插拔；上層 AutoChunker 依內容類型挑選
  - 不強制 CJK 或英文，全部以「字符」為單位 + 補語意邊界偵測
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class Chunk:
    """單一切片單元。"""
    content:        str
    char_start:     int           = 0           # 在原文中的起始位移
    char_end:       int           = 0
    heading_path:   list[str]     = field(default_factory=list)  # ["第一章", "1.2 條"]
    chunk_type:     str           = "text"      # text / table / qa / code / image_ref
    meta:           dict          = field(default_factory=dict)


class Chunker(Protocol):
    """切片器協議。"""
    name: str
    def split(self, text: str) -> list[Chunk]: ...


# 公用 CJK / 英文邊界偵測 ─────────────────────────────────────────────

# CJK 句末符號：句號、問號、驚嘆號、頓號、分號（中英文兼容）
_SENT_END = "。！？；!?;"
_PAUSE    = "，、 "

# 是否為 CJK 字符
def is_cjk(ch: str) -> bool:
    if not ch: return False
    code = ord(ch)
    return (
        0x4E00 <= code <= 0x9FFF or      # CJK Unified
        0x3400 <= code <= 0x4DBF or      # Extension A
        0x3000 <= code <= 0x303F or      # Punctuation
        0x3040 <= code <= 0x30FF or      # Hiragana / Katakana
        0xFF00 <= code <= 0xFFEF         # Full-width forms
    )


def find_prev_sentence_end(text: str, start: int) -> int:
    """從 start 位置往前找最近一個句末符；找不到則回 -1。"""
    for i in range(start - 1, -1, -1):
        if text[i] in _SENT_END:
            return i
    return -1


def find_next_sentence_end(text: str, start: int) -> int:
    """從 start 位置往後找最近一個句末符；找不到回 len(text)-1。"""
    for i in range(start, len(text)):
        if text[i] in _SENT_END:
            return i
    return len(text) - 1


def normalize_whitespace(text: str) -> str:
    """壓縮多餘空白，但保留段落（連續 \\n+ → \\n\\n）。"""
    import re
    # 多重 \n 壓成 2 個
    text = re.sub(r"\n{3,}", "\n\n", text)
    # 行內多空白壓成 1
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()
