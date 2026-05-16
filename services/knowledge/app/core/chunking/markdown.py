"""Markdown-aware 切片器 — 保留 heading 階層脈絡。

技術重點（原創實作，依 CommonMark 結構通則）：
  1. 掃描每一行的 #-level heading，維護階層 stack
  2. 同一個 heading 段落內若仍過長，遞迴交給 RecursiveChunker 切
  3. 每個輸出 chunk 都帶 heading_path（["第一章", "1.2 條"]），給 RAG
     在 prompt 中還原上下文（"在「第一章 / 1.2 條」中提到…"）
  4. Fenced code block（``` 開頭）整段保留為單一 chunk，不被切
  5. Markdown table（以 | 開頭的連續行）整段保留，僅在超過 chunk_size
     時降回 recursive
"""
from __future__ import annotations

import re

from .base import Chunk
from .recursive import RecursiveChunker


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_FENCE_OPEN_RE = re.compile(r"^\s*```")
_TABLE_LINE_RE = re.compile(r"^\s*\|")


class MarkdownChunker:
    name = "markdown"

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._fallback = RecursiveChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    def split(self, text: str) -> list[Chunk]:
        if not text.strip():
            return []

        # ── 第 1 步：依「heading 與 fenced block 邊界」切大區段 ────
        segments = self._segment_by_structure(text)

        # ── 第 2 步：每段過長就交給 RecursiveChunker 細切，並繼承 heading_path
        all_chunks: list[Chunk] = []
        for seg in segments:
            seg_text = seg["text"].strip()
            if not seg_text:
                continue
            kind = seg["kind"]               # 'code' | 'table' | 'prose'
            path = seg["heading_path"]

            if kind in ("code", "table") and len(seg_text) <= self.chunk_size * 2:
                # 程式碼/表格優先保完整，超過 2x 才放棄
                all_chunks.append(Chunk(
                    content=seg_text,
                    chunk_type=kind,
                    heading_path=path,
                ))
                continue

            if len(seg_text) <= self.chunk_size:
                all_chunks.append(Chunk(
                    content=seg_text,
                    chunk_type="text",
                    heading_path=path,
                ))
                continue

            # 過長 → recursive 細切；繼承 heading_path
            sub = self._fallback.split(seg_text)
            for s in sub:
                s.heading_path = list(path)
                all_chunks.append(s)

        return all_chunks

    # ── 第 1 步實作：以 heading / fence 為邊界把文本切成段落 ─────
    def _segment_by_structure(self, text: str) -> list[dict]:
        lines = text.split("\n")
        heading_stack: list[str] = []        # depth-indexed heading titles
        segments: list[dict] = []
        buf: list[str] = []
        cur_kind = "prose"

        def flush(kind: str):
            if buf:
                segments.append({
                    "kind": kind,
                    "text": "\n".join(buf),
                    "heading_path": list(heading_stack),
                })
                buf.clear()

        i = 0
        n = len(lines)
        while i < n:
            line = lines[i]
            # ── fenced code block：``` ... ```
            if _FENCE_OPEN_RE.match(line):
                flush(cur_kind)
                code_buf = [line]
                i += 1
                while i < n and not _FENCE_OPEN_RE.match(lines[i]):
                    code_buf.append(lines[i])
                    i += 1
                if i < n:
                    code_buf.append(lines[i])         # 收尾的 ```
                    i += 1
                segments.append({
                    "kind": "code",
                    "text": "\n".join(code_buf),
                    "heading_path": list(heading_stack),
                })
                continue

            # ── heading：把當前 buf 收掉再更新 stack
            m = _HEADING_RE.match(line)
            if m:
                flush(cur_kind)
                depth = len(m.group(1))
                title = m.group(2).strip()
                # 截斷 stack 到對應深度後 append
                heading_stack = heading_stack[: depth - 1] + [title]
                # heading 自身作為 1 個 chunk-seed（給 retrieval 增加 anchor）
                segments.append({
                    "kind": "prose",
                    "text": "#" * depth + " " + title,
                    "heading_path": list(heading_stack),
                })
                i += 1
                continue

            # ── markdown table：連續以 | 開頭的行整段聚合
            if _TABLE_LINE_RE.match(line):
                flush(cur_kind)
                tbl = []
                while i < n and _TABLE_LINE_RE.match(lines[i]):
                    tbl.append(lines[i])
                    i += 1
                segments.append({
                    "kind": "table",
                    "text": "\n".join(tbl),
                    "heading_path": list(heading_stack),
                })
                continue

            # ── 一般 prose
            buf.append(line)
            cur_kind = "prose"
            i += 1

        flush(cur_kind)
        return segments
