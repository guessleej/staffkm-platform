"""document_processor 純邏輯單元測試 — magic byte sniff + 文字分段。

不需 DB / 重型 deps（pypdf/openpyxl/tesseract 都是 method 內 lazy import）。
"""
from __future__ import annotations

import sys
from pathlib import Path

# 讓 test 能 import service 的 app.core
_SVC = Path(__file__).resolve().parent.parent  # services/knowledge
if str(_SVC) not in sys.path:
    sys.path.insert(0, str(_SVC))

from app.core.document_processor import DocumentProcessor, TextSplitter  # noqa: E402


# ── magic byte sniff ─────────────────────────────────────────────────
def test_sniff_pdf():
    assert DocumentProcessor._sniff(b"%PDF-1.7", ".pdf") == ".pdf"


def test_sniff_png():
    assert DocumentProcessor._sniff(b"\x89PNG\r\n\x1a\n", ".png") == ".png"


def test_sniff_jpeg():
    assert DocumentProcessor._sniff(b"\xff\xd8\xff\xe0", ".jpg") == ".jpg"


def test_sniff_docx_vs_xlsx_by_ext():
    # 都是 PK ZIP 容器，靠副檔名區分
    pk = b"PK\x03\x04abcd"
    assert DocumentProcessor._sniff(pk, ".xlsx") == ".xlsx"
    assert DocumentProcessor._sniff(pk, ".docx") == ".docx"


def test_sniff_ole2_xls_not_rejected():
    # v5.9.19: 舊版 .xls 不再 raise，回 .xls
    ole2 = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
    assert DocumentProcessor._sniff(ole2, ".xls") == ".xls"
    assert DocumentProcessor._sniff(ole2, ".doc") == ".doc"


def test_sniff_plaintext_fallback():
    assert DocumentProcessor._sniff(b"hello world", ".txt") == ".txt"
    assert DocumentProcessor._sniff(b"# heading", ".md") == ".md"


def test_image_extensions_in_loaders():
    # v5.9.22 OCR：圖片格式都註冊到 LOADERS
    for ext in (".png", ".jpg", ".jpeg", ".webp", ".tiff", ".bmp"):
        assert ext in DocumentProcessor.LOADERS
        assert DocumentProcessor.LOADERS[ext] == "_load_image"
    # .xls (v5.9.19) + .html
    assert DocumentProcessor.LOADERS.get(".xls") == "_load_xls_legacy"
    assert ".html" in DocumentProcessor.LOADERS


# ── 文字分段 ─────────────────────────────────────────────────────────
def test_splitter_basic():
    sp = TextSplitter(chunk_size=20, chunk_overlap=5)
    chunks = sp.split("一二三四五六七八九十。" * 5)
    assert len(chunks) >= 2
    assert all(len(c) <= 40 for c in chunks)  # 寬鬆上界（含 overlap）


def test_splitter_empty():
    sp = TextSplitter(chunk_size=512, chunk_overlap=64)
    assert sp.split("") == [] or sp.split("") == [""]


def test_splitter_short_text_single_chunk():
    sp = TextSplitter(chunk_size=512, chunk_overlap=64)
    chunks = sp.split("短文字")
    assert len(chunks) == 1
    assert chunks[0] == "短文字"
