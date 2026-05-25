"""SSE 串流換行守衛 — 對話回答換行已回歸 3 次，這支把整條鏈的不變式固化。

回歸史（每次都讓答案「擠成一坨」/逐字斷行）：
- v5.9.32：sse-starlette 用 CRLF，前端 parser 沒去尾 \\r → 每 token 帶 \\r。
- v5.10.13：token 內含換行被 sse-starlette 拆成多行 data:，中繼/前端用 .strip() 或
            只取單行 → 換行全失。修法：逐 event 累積 data: 行、用 \\n 重組。
- v5.11.6：地端模型（gemma4）把換行單獨當 token 串（純 "\\n"/"\\n\\n"），SSE 規範
            會吃掉 data 值結尾的 \\n → 換行遺失。修法：agent 把結尾換行留到下一個
            有內容的 token 前面（split_trailing_newlines）→ 換行變「內部換行」。

兩層守衛：
(A) 行為 round-trip：模擬整條 SSE 鏈，斷言三類換行都活著（純邏輯、不依賴 live stack）。
(B) 原始碼守衛：把每個防護點綁到實際程式（移掉任一防護就 CI 紅）。

CI backend job 只裝 pytest/ruff/structlog/charset-normalizer（無 openai/httpx），
故本檔自包含、不 import 服務模組。
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB_SRC = ROOT / "apps" / "web" / "src"


# ── 自包含複本：必須與 base_agent.split_trailing_newlines 行為一致 ─────────────
# （守衛 B 會斷言實際程式仍有此防護；此處是行為測試用的純邏輯參照）
def _split_trailing_newlines(s: str) -> tuple[str, str]:
    i = len(s)
    while i > 0 and s[i - 1] == "\n":
        i -= 1
    return s[:i], s[i:]


def _sse_encode_event(data: str, *, eol: str = "\r\n") -> str:
    """模擬 sse-starlette：data 依 \\n 拆成多行 data:，行尾預設 CRLF（重現 v5.9.32）。"""
    body = "".join(f"data: {line}{eol}" for line in data.split("\n"))
    return f"event: token{eol}{body}{eol}"  # 末尾空行 = event 邊界


def _sse_parse_text(raw: str) -> str:
    """模擬中繼/前端的事件感知解析：去尾 \\r、逐 event 累積 data: 行、用 \\n 重組。

    這正是 conversations.py 中繼與 apps/web/src/api/chat.ts 前端的契約。
    """
    out: list[str] = []
    data_lines: list[str] = []
    ev = ""

    def flush():
        nonlocal ev, data_lines
        if not ev and not data_lines:
            return
        data = "\n".join(data_lines)
        ev, data_lines = "", []
        # 修正後 receiver 的契約：真正空事件（data=="")才跳過；純換行（data 非空）必須保留。
        # v5.11.6 根因正是「把純換行 token 當空/結束丟掉」。
        if data == "":
            return
        out.append(data)

    for raw_line in raw.split("\n"):
        line = raw_line.rstrip("\r")          # v5.9.32：必須去尾 \r
        if line == "":
            flush()
            continue
        if line.startswith("event:"):
            ev = line[6:].lstrip()
        elif line.startswith("data:"):
            s = line[5:]
            data_lines.append(s[1:] if s.startswith(" ") else s)  # 去一個分隔空格
    flush()
    return "".join(out)


def _stream_through_chain(deltas: list[str]) -> str:
    """gemma4 風格 deltas → agent buffering → 每 token 過兩跳 SSE（agent→中繼→前端）。"""
    pending = ""
    tokens: list[str] = []
    for d in deltas:
        head, pending = _split_trailing_newlines(pending + d)
        if head:
            tokens.append(head)
    # 每個 token 經中繼一跳、前端一跳（與線上拓撲一致）
    return "".join(_sse_parse_text(_sse_encode_event(_sse_parse_text(_sse_encode_event(t)))) for t in tokens)


# ════════════════════════════════════════════════════════════════════════════
# (A) 行為 round-trip — 三類回歸都要擋住
# ════════════════════════════════════════════════════════════════════════════

def test_split_trailing_newlines_contract():
    """head 不得以 \\n 結尾，且 head + trail == 原字串（v5.11.6 核心不變式）。"""
    for s in ["a", "a\n", "a\n\n", "\n", "\n\n", "", "a\nb", "a\nb\n", "## x\n\n"]:
        head, trail = _split_trailing_newlines(s)
        assert head + trail == s
        assert not head.endswith("\n"), f"head 仍以換行結尾：{head!r}"
        assert set(trail) <= {"\n"}, f"trail 應只含換行：{trail!r}"


def test_standalone_newline_tokens_survive_chain():
    """v5.11.6：地端模型把換行單獨成 token，經整條鏈後換行必須保留。"""
    deltas = ["請假步驟：", "\n\n", "## 一、準備", "\n", "查規定", "\n\n", "## 二、送出", "\n", "等核准"]
    expected = "".join(deltas).rstrip("\n")
    got = _stream_through_chain(deltas)
    assert got == expected, f"換行在 SSE 鏈遺失\n expected={expected!r}\n got={got!r}"
    assert got.count("\n") == expected.count("\n") >= 4


def test_multiline_data_token_preserved():
    """v5.10.13：單一 token 內含多個換行（內部換行），重組後不得丟。"""
    deltas = ["第一段\n\n第二段\n- 項目A\n- 項目B"]
    got = _stream_through_chain(deltas)
    assert got == "第一段\n\n第二段\n- 項目A\n- 項目B"


def test_crlf_not_leaked_into_text():
    """v5.9.32：CRLF 行尾不得把 \\r 漏進重組後的文字。"""
    got = _stream_through_chain(["標題", "\n", "內文一", "\n", "內文二"])
    assert "\r" not in got, f"重組文字殘留 \\r：{got!r}"
    assert got == "標題\n內文一\n內文二"


def test_plain_text_unchanged():
    """無換行的純文字 token 不應被動到。"""
    assert _stream_through_chain(["你好", "，", "世界"]) == "你好，世界"


def test_pure_newline_token_not_dropped_by_receiver():
    """v5.11.6 根因守衛：純換行 token 經 receiver 不可被當『空/結束』丟掉。

    這是換行遺失的真正根因（前端 `!trimmed` → onDone）。agent 緩衝是一層防護，
    receiver 不丟純換行是另一層；兩層任一失守都會回歸 → 都要守。
    """
    assert _sse_parse_text(_sse_encode_event("\n\n")) == "\n\n"
    assert _sse_parse_text(_sse_encode_event("\n")) == "\n"
    assert _sse_parse_text(_sse_encode_event("")) == ""   # 真正空事件才該被吃掉


# ════════════════════════════════════════════════════════════════════════════
# (B) 原始碼守衛 — 把防護綁到實際程式（移掉就紅）
# ════════════════════════════════════════════════════════════════════════════

def test_agent_buffers_trailing_newlines():
    """v5.11.6：base_agent 須定義 split_trailing_newlines，且兩條 agent 串流路徑都用。"""
    base = ROOT / "services/agent/app/core/base_agent.py"
    appa = ROOT / "services/agent/app/core/application_agent.py"
    if not base.exists():
        return
    bt = base.read_text(encoding="utf-8", errors="ignore")
    assert "def split_trailing_newlines" in bt, "base_agent 缺 split_trailing_newlines 定義"
    assert bt.count("split_trailing_newlines") >= 2, "base_agent 定義了但沒在串流迴圈用"
    if appa.exists():
        at = appa.read_text(encoding="utf-8", errors="ignore")
        # 兩個串流迴圈（stream_events 的 simple + function_calling 路徑）都要用
        assert at.count("split_trailing_newlines") >= 2, \
            "application_agent 的串流迴圈未套用換行緩衝（v5.11.6 會回歸）"


def test_chat_relay_rejoins_multiline_data():
    """v5.10.13：chat 中繼須用 \\n 重組多行 data 且去尾 \\r，不可用 .strip() 砍換行。"""
    relay = ROOT / "services/chat/app/api/conversations.py"
    if not relay.exists():
        return
    t = relay.read_text(encoding="utf-8", errors="ignore")
    assert '"\\n".join(data_lines)' in t or "'\\n'.join(data_lines)" in t, \
        "chat 中繼未用 \\n 重組多行 data"
    assert 'rstrip("\\r")' in t or "rstrip('\\r')" in t, "chat 中繼未去尾 \\r"


def test_frontend_rejoins_multiline_data():
    """v5.10.13：前端 SSE parser 須用 \\n 重組多行 data。"""
    chat_ts = WEB_SRC / "api" / "chat.ts"
    if not chat_ts.exists():
        return
    t = chat_ts.read_text(encoding="utf-8", errors="ignore")
    assert "dataLines.join('\\n')" in t or 'dataLines.join("\\n")' in t, \
        "前端 chat.ts 未用 \\n 重組多行 data（v5.10.13 會回歸）"


def test_frontend_does_not_treat_empty_as_done():
    """v5.11.6 根因守衛：前端不可用空白/空字串判斷觸發 onDone（會丟純換行 token）。"""
    chat_ts = WEB_SRC / "api" / "chat.ts"
    if not chat_ts.exists():
        return
    t = chat_ts.read_text(encoding="utf-8", errors="ignore")
    bad = ["!trimmed ||", "if (!trimmed)", "!data.trim()"]
    found = [b for b in bad if b in t]
    assert not found, ("前端又用空白判斷當 done → 純換行 token 會被丟（v5.11.6 根因回歸）："
                       + ", ".join(found))


def test_sse_parsers_strip_carriage_return():
    """v5.9.32：凡用 line.slice(N) 抽 SSE data 的前端檔，同檔必須有去 \\r 處理。"""
    if not WEB_SRC.exists():
        return
    slice_pat = re.compile(r"line\.slice\(\s*[56]\s*\)")
    hits = []
    for p in list(WEB_SRC.rglob("*.vue")) + list(WEB_SRC.rglob("*.ts")):
        text = p.read_text(encoding="utf-8", errors="ignore")
        if not slice_pat.search(text):
            continue
        if not re.search(r"replace\(\s*/\\r|\.trim\(\)|replaceAll\(\s*['\"]\\r", text):
            hits.append(str(p.relative_to(ROOT)))
    assert not hits, "SSE parser 用 line.slice 但沒去尾 \\r:\n" + "\n".join(hits)
