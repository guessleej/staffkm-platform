"""SSE CRLF 守衛 — 確保前端 SSE token parser 有去尾 \\r。

v5.9.32 雷：sse-starlette 用 CRLF (\\r\\n)，parser 用 line.slice(6) 沒去 \\r
→ 每 token 帶 \\r → marked 當換行 → 對話逐字斷行。
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB_SRC = ROOT / "apps" / "web" / "src"


def test_sse_parsers_strip_carriage_return():
    """凡是用 line.slice(N) 抽 SSE data 的，同檔必須有去 \\r 處理。"""
    if not WEB_SRC.exists():
        return
    slice_pat = re.compile(r"line\.slice\(\s*[56]\s*\)")
    hits = []
    for p in list(WEB_SRC.rglob("*.vue")) + list(WEB_SRC.rglob("*.ts")):
        text = p.read_text(encoding="utf-8", errors="ignore")
        if not slice_pat.search(text):
            continue
        # 必須有去 \r 的處理：replace(/\r$/) 或 .trim() 或 replaceAll
        if not re.search(r"replace\(\s*/\\r|\.trim\(\)|replaceAll\(\s*['\"]\\r", text):
            hits.append(str(p.relative_to(ROOT)))
    assert not hits, "SSE parser 用 line.slice 但沒去尾 \\r:\n" + "\n".join(hits)
