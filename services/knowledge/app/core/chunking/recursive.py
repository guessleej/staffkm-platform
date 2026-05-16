"""遞迴字符切片器（CJK-aware）— 原創實作。

設計重點：
  1. 依「段落 → 句子 → 子句 → 詞 → 字」優先順序遞迴切割
  2. 達到 chunk_size 時不在句子中間斷開（盡可能找最近的句末符回退）
  3. Overlap 採「句子對齊」而非字元對齊，避免半句重複造成 embedding 雜訊
  4. CJK 與英文混排自動適應，不需要分詞工具
  5. 不引入外部依賴（標準庫即可）
"""
from __future__ import annotations

from .base import Chunk, _SENT_END, normalize_whitespace


# 依優先序的分隔符（CJK + 英文皆兼容）
_SEPARATORS_DEFAULT: list[str] = [
    "\n\n\n",  # 多重換行（強分段）
    "\n\n",    # 段落
    "\n",      # 行
    "。", "！", "？",          # CJK 句末
    ".", "!", "?",              # ASCII 句末
    "；", ";",                  # 分號
    "，", ",",                  # 逗號
    " ",                        # 空白
    "",                         # 字元級回退
]


class RecursiveChunker:
    name = "recursive"

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        separators: list[str] | None = None,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = min(chunk_overlap, chunk_size - 1)
        self.separators = separators or _SEPARATORS_DEFAULT

    # ── 對外入口 ─────────────────────────────────────────────────────
    def split(self, text: str) -> list[Chunk]:
        normalized = normalize_whitespace(text)
        if not normalized:
            return []
        raw = self._split_recursive(normalized, self.separators)
        chunks = self._apply_sentence_aligned_overlap(raw)
        return self._with_offsets(normalized, chunks)

    # ── 核心遞迴 ─────────────────────────────────────────────────────
    def _split_recursive(self, text: str, seps: list[str]) -> list[str]:
        if len(text) <= self.chunk_size:
            return [text] if text.strip() else []

        sep = seps[0] if seps else ""
        parts = text.split(sep) if sep else list(text)

        out: list[str] = []
        buf = ""

        for p in parts:
            cand = buf + (sep if buf else "") + p
            if len(cand) <= self.chunk_size:
                buf = cand
                continue
            # 超過：把 buf 收掉
            if buf:
                out.append(buf)
                buf = ""
            # 單個 part 仍過長 → 用下一級分隔符繼續切
            if len(p) > self.chunk_size and len(seps) > 1:
                out.extend(self._split_recursive(p, seps[1:]))
            else:
                # 找不到更細的分隔符可用 → 直接硬切，但盡量找句末退一步
                out.extend(self._hard_chunk_at_sentence(p))

        if buf:
            out.append(buf)
        return [c.strip() for c in out if c.strip()]

    # ── 硬切時優先在句末斷 ───────────────────────────────────────────
    def _hard_chunk_at_sentence(self, text: str) -> list[str]:
        """text 已比 chunk_size 大且找不到更細分隔符；
        盡量在句末符之前斷開，最差才字元硬切。"""
        result: list[str] = []
        i = 0
        n = len(text)
        while i < n:
            end = min(i + self.chunk_size, n)
            if end < n:
                # 從 end 往回最多 chunk_size//4 找句末符
                back_limit = max(i + 1, end - max(self.chunk_size // 4, 32))
                cut = -1
                for j in range(end - 1, back_limit - 1, -1):
                    if text[j] in _SENT_END:
                        cut = j + 1  # 包含句末符
                        break
                if cut == -1:
                    cut = end
            else:
                cut = end
            piece = text[i:cut].strip()
            if piece:
                result.append(piece)
            i = cut
        return result

    # ── 句子對齊的 overlap ───────────────────────────────────────────
    def _apply_sentence_aligned_overlap(self, chunks: list[str]) -> list[str]:
        """把前一個 chunk 結尾的「最後一句」（或截斷至 chunk_overlap 長度）
        prepend 到當前 chunk，比純字元 overlap 更穩定。"""
        if self.chunk_overlap <= 0 or len(chunks) <= 1:
            return chunks

        out = [chunks[0]]
        for i in range(1, len(chunks)):
            prev = chunks[i - 1]
            # 取 prev 最尾部的 chunk_overlap 範圍，並從句末符往後對齊
            tail = prev[-self.chunk_overlap:]
            # 嘗試找第一個句末符切點，從那之後作 overlap
            cut = -1
            for j, ch in enumerate(tail):
                if ch in _SENT_END:
                    cut = j + 1
                    break
            overlap = tail[cut:] if 0 <= cut < len(tail) else tail
            overlap = overlap.strip()
            if overlap:
                out.append(overlap + "\n" + chunks[i])
            else:
                out.append(chunks[i])
        return out

    # ── 還原 char offsets 給每個 chunk（利後續 citation highlight）─
    def _with_offsets(self, normalized: str, raw_chunks: list[str]) -> list[Chunk]:
        chunks: list[Chunk] = []
        cursor = 0
        for c in raw_chunks:
            # 找 c 在 normalized 中的位置（從 cursor 開始）
            idx = normalized.find(c.split("\n", 1)[0][:32], cursor) if c else -1
            start = idx if idx >= 0 else cursor
            end = start + len(c)
            chunks.append(Chunk(
                content=c,
                char_start=start,
                char_end=end,
                chunk_type="text",
            ))
            cursor = end
        return chunks
