"""文件處理核心 — 載入、分段、向量化"""
import io
from pathlib import Path
from typing import BinaryIO

import structlog

log = structlog.get_logger()


class DocumentProcessor:
    """支援 PDF、Word、Excel、Markdown、TXT 的文件載入器。"""

    LOADERS: dict[str, str] = {
        ".pdf": "_load_pdf",
        ".docx": "_load_docx",
        ".doc":  "_load_doc_legacy",   # OLE2 → antiword
        ".xlsx": "_load_excel",
        ".xls":  "_load_xls_legacy",   # v5.9.19: OLE2 舊版 Excel → xlrd
        ".csv":  "_load_csv",
        ".md":   "_load_text",
        ".txt":  "_load_text",
    }

    def load(self, file: BinaryIO, filename: str) -> str:
        ext = Path(filename).suffix.lower()
        # 以 magic bytes 偵測真實格式（副檔名常常與內容不符）
        head = file.read(8)
        file.seek(0)
        actual = self._sniff(head, ext)

        method_name = self.LOADERS.get(actual)
        if not method_name:
            raise ValueError(
                f"不支援的檔案格式：{ext}（內容偵測為 {actual or '未知'}）。"
                f"請另存為 .docx / .pdf / .txt 後再上傳。"
            )
        return getattr(self, method_name)(file)

    @staticmethod
    def _sniff(head: bytes, ext: str) -> str:
        """以 magic bytes 偵測實際檔案格式，副檔名作為輔助。"""
        # PDF: %PDF
        if head.startswith(b"%PDF"):
            return ".pdf"
        # DOCX/XLSX 等 Office Open XML：PK ZIP 容器
        if head.startswith(b"PK\x03\x04") or head.startswith(b"PK\x05\x06"):
            # 同樣是 PK，需以副檔名區分 docx / xlsx
            if ext in (".xlsx",):
                return ".xlsx"
            return ".docx"
        # 舊版 OLE2 (.doc / .xls)：D0 CF 11 E0 A1 B1 1A E1
        if head.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
            # v5.9.19: 加 xlrd 支援，.xls 不再 raise
            if ext == ".xls":
                return ".xls"
            return ".doc"
        # 純文字 / Markdown / CSV 沒有固定 magic bytes
        if ext in (".txt", ".md", ".csv"):
            return ext
        # 已知文字內容 → 視為 txt
        try:
            head.decode("utf-8")
            return ".txt"
        except UnicodeDecodeError:
            return ext  # 最終回退到副檔名

    def _load_pdf(self, file: BinaryIO) -> str:
        from pypdf import PdfReader
        reader = PdfReader(file)
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)

    def _load_docx(self, file: BinaryIO) -> str:
        from docx import Document
        try:
            doc = Document(file)
        except Exception as e:
            raise ValueError(
                f"Word 文件解析失敗（{e}）。請確認檔案未損毀，或以 Word 開啟後另存為 .docx 再上傳。"
            )
        return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())

    def _load_doc_legacy(self, file: BinaryIO) -> str:
        """舊版 .doc (OLE2) 用 antiword 解析。"""
        import subprocess, tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".doc", delete=False) as tmp:
            tmp.write(file.read())
            tmp_path = tmp.name
        try:
            result = subprocess.run(
                ["antiword", "-w", "0", "-m", "UTF-8.txt", tmp_path],
                capture_output=True, timeout=60,
            )
            if result.returncode != 0:
                stderr = result.stderr.decode("utf-8", errors="replace").strip()
                raise ValueError(
                    f"antiword 解析失敗：{stderr or '未知錯誤'}。"
                    f"建議以 Word 開啟後另存為 .docx 再上傳。"
                )
            return result.stdout.decode("utf-8", errors="replace")
        finally:
            try: os.unlink(tmp_path)
            except OSError: pass

    def _load_excel(self, file: BinaryIO) -> str:
        import openpyxl
        wb = openpyxl.load_workbook(file, read_only=True)
        rows = []
        for ws in wb.worksheets:
            for row in ws.iter_rows(values_only=True):
                cells = [str(c) for c in row if c is not None]
                if cells:
                    rows.append("\t".join(cells))
        return "\n".join(rows)

    def _load_xls_legacy(self, file: BinaryIO) -> str:
        """v5.9.19: 舊版 .xls (OLE2) 用 xlrd 2.x 解析。"""
        try:
            import xlrd
        except ImportError as e:
            raise ValueError(
                "舊版 Excel (.xls) 解析需 xlrd library — 環境未安裝。"
                "請以 Excel 開啟後另存為 .xlsx 再上傳。"
            ) from e
        try:
            data = file.read()
            wb = xlrd.open_workbook(file_contents=data)
        except Exception as e:
            raise ValueError(
                f"舊版 Excel (.xls) 解析失敗：{e}。"
                "請確認檔案未損毀，或以 Excel 開啟後另存為 .xlsx 再上傳。"
            )
        rows = []
        for sheet in wb.sheets():
            for r_idx in range(sheet.nrows):
                cells = []
                for c in sheet.row_values(r_idx):
                    if c == "" or c is None:
                        continue
                    cells.append(str(c))
                if cells:
                    rows.append("\t".join(cells))
        return "\n".join(rows)

    def _load_csv(self, file: BinaryIO) -> str:
        import csv
        content = file.read().decode("utf-8-sig")
        reader = csv.reader(io.StringIO(content))
        return "\n".join("\t".join(row) for row in reader)

    def _load_text(self, file: BinaryIO) -> str:
        return file.read().decode("utf-8", errors="replace")


class TextSplitter:
    """針對繁體中文優化的遞迴分段器。"""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        # 依優先順序的分段符號 (繁體中文適用)
        self.separators = ["\n\n", "\n", "。", "！", "？", "；", " ", ""]

    def split(self, text: str) -> list[str]:
        return self._split_recursive(text.strip(), self.separators)

    def _split_recursive(self, text: str, separators: list[str]) -> list[str]:
        if len(text) <= self.chunk_size:
            return [text] if text else []

        separator = separators[0] if separators else ""
        splits = text.split(separator) if separator else list(text)

        chunks: list[str] = []
        current = ""

        for split in splits:
            candidate = current + (separator if current else "") + split
            if len(candidate) <= self.chunk_size:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                if len(split) > self.chunk_size and len(separators) > 1:
                    chunks.extend(self._split_recursive(split, separators[1:]))
                    current = ""
                else:
                    current = split

        if current:
            chunks.append(current)

        # 加入重疊
        if self.chunk_overlap > 0 and len(chunks) > 1:
            chunks = self._apply_overlap(chunks)

        return chunks

    def _apply_overlap(self, chunks: list[str]) -> list[str]:
        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_tail = chunks[i - 1][-self.chunk_overlap:]
            overlapped.append(prev_tail + chunks[i])
        return overlapped
