"""document_processor 純邏輯單元測試 — magic byte sniff + 文字分段。

不需 DB / 重型 deps（pypdf/openpyxl/tesseract 都是 method 內 lazy import）。
"""
from __future__ import annotations

import io
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


# ── 編碼偵測：台灣公文 Big5 / CP950 round-trip ───────────────────────
# 混合中文 + 全形標點 + ASCII，模擬政府採購清單常見內容
_BIG5_SAMPLE = "固態硬碟 M.2 USSD A400（全形括號）型號：ABC-123\n品名\t單價\t數量"
# U+FFFD replacement char — 出現代表解碼失敗 / mojibake
_MOJIBAKE_MARKERS = ("�", "º", "µ", "Ð", "½", "»")


def _has_mojibake(text: str) -> bool:
    return any(m in text for m in _MOJIBAKE_MARKERS)


def test_decode_bytes_utf8_passthrough():
    data = _BIG5_SAMPLE.encode("utf-8")
    assert DocumentProcessor._decode_bytes(data) == _BIG5_SAMPLE


def test_decode_bytes_big5_roundtrip():
    data = _BIG5_SAMPLE.encode("big5")
    out = DocumentProcessor._decode_bytes(data)
    assert out == _BIG5_SAMPLE
    assert not _has_mojibake(out)


def test_decode_bytes_empty():
    assert DocumentProcessor._decode_bytes(b"") == ""


def test_decode_bytes_gb18030_simplified():
    # 簡中走 charset-normalizer 偵測路徑 → 沒裝 charset-normalizer 時跳過
    # （big5/cp950 fallback 是純 stdlib，不需此 guard；GB18030 區辨才需偵測器）。
    # 注意：極短字串（如 6 字）在 Big5/GB byte range 上同時合法、本質無法區分，
    # 本產品以台灣 Big5 為主刻意偏向 Big5；故此處用足夠長度的樣本讓偵測有訊號可判。
    import pytest
    pytest.importorskip("charset_normalizer")
    sample = "固态硬盘测试数据中心服务器内存条简体中文样本编码侦测"
    out = DocumentProcessor._decode_bytes(sample.encode("gb18030"))
    assert out == sample
    assert not _has_mojibake(out)


def test_load_txt_big5_no_mojibake():
    """ingest 一個 Big5 編碼的 .txt → 抽出文字正確、無亂碼。"""
    proc = DocumentProcessor()
    raw = _BIG5_SAMPLE.encode("big5")
    out = proc.load(io.BytesIO(raw), "公文.txt")
    assert "固態硬碟" in out
    assert "（全形括號）" in out
    assert not _has_mojibake(out)


def test_load_csv_big5_no_mojibake():
    """ingest 一個 Big5 編碼的 .csv → 欄位中文正確、無亂碼。"""
    proc = DocumentProcessor()
    csv_text = "品名,單價,數量\n固態硬碟,1200,5\n記憶體模組,800,10"
    raw = csv_text.encode("big5")
    out = proc.load(io.BytesIO(raw), "採購清單.csv")
    assert "固態硬碟" in out
    assert "記憶體模組" in out
    assert not _has_mojibake(out)
