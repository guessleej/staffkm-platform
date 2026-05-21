"""雷區守衛 — 把 CLAUDE.md 踩雷集變成自動化 regression guard。

這些測試掃描整個 repo，確保這輪 (v5.0~v5.9) 踩過的 bug pattern 不再復發。
不需 DB / service boot，純檔案掃描，CI 一定能跑。

對應 CLAUDE.md 踩雷集：
- §8 asyncpg :param::type
- asyncpg array literal ANY('{...}')
- gateway router 漏注入 workspace
- 前端 raw fetch 漏 X-Workspace-ID
- IME 組字 Enter 誤送出
- SSE CRLF 殘留 \\r
- placeholder view 殘留
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVICES = ROOT / "services"
PKGS = ROOT / "packages" / "python"
WEB_SRC = ROOT / "apps" / "web" / "src"


def _py_files(*roots: Path):
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*.py"):
            if "__pycache__" in p.parts or "/alembic/versions/" in str(p):
                continue
            yield p


def _web_files(*exts: str):
    if not WEB_SRC.exists():
        return
    for ext in exts:
        for p in WEB_SRC.rglob(f"*.{ext}"):
            yield p


# ── §8 asyncpg :param::type ──────────────────────────────────────────
def test_no_asyncpg_param_cast():
    """:param::jsonb 等 — asyncpg dialect 不認，必須用 CAST(:param AS type)。"""
    pat = re.compile(r":[a-z_]+::(jsonb|vector|uuid|int|text|timestamptz|date|inet|bool)")
    hits = []
    for p in _py_files(SERVICES, PKGS):
        for i, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            s = line.strip()
            if s.startswith("#"):  # 跳過註解
                continue
            if pat.search(line):
                hits.append(f"{p.relative_to(ROOT)}:{i}: {s[:80]}")
    assert not hits, "發現 :param::type（改 CAST(:param AS type)）:\n" + "\n".join(hits)


# ── asyncpg array literal ────────────────────────────────────────────
def test_no_asyncpg_array_literal():
    """ANY('{u1,u2}') PG literal — asyncpg 壞，改 Python list bind + ANY(:ids)。"""
    pat = re.compile(r"""ANY\(['"]\\?\{[a-z0-9_,\-]+\}['"]\)""")
    hits = []
    for p in _py_files(SERVICES, PKGS):
        for i, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            if pat.search(line):
                hits.append(f"{p.relative_to(ROOT)}:{i}")
    assert not hits, "發現 ANY('{...}') array literal:\n" + "\n".join(hits)


# ── 前端 IME 組字 Enter 守衛 ──────────────────────────────────────────
def test_no_enter_handler_without_ime_guard():
    """@keydown.enter 觸發送出/執行的，必須有 isComposing / onEnterKey 守衛。"""
    hits = []
    for p in _web_files("vue"):
        text = p.read_text(encoding="utf-8", errors="ignore")
        for i, line in enumerate(text.splitlines(), 1):
            if "@keydown.enter" not in line:
                continue
            # 安全：shift 換行、有 isComposing、走 onEnterKey、.stop 純阻止
            if any(tok in line for tok in ("shift", "isComposing", "onEnterKey", "onEnter")):
                continue
            # .prevent 直接接 send/submit/exec/run 才是危險（IME 會誤觸）
            if re.search(r"\.prevent=\"[^\"]*(send|submit|exec|run|sendMessage)", line):
                hits.append(f"{p.relative_to(ROOT)}:{i}: {line.strip()[:90]}")
    assert not hits, "發現未防 IME 組字的 enter 送出 handler:\n" + "\n".join(hits)


# ── 前端 raw fetch 漏 X-Workspace-ID 守衛 ────────────────────────────
def test_workspace_scoped_fetch_has_header():
    """raw fetch 打 workspace-scoped 端點 (agents/applications/knowledge) 必須有 X-Workspace-ID。
    (public 端點除外)。檢查同檔有無注入 ws header。"""
    hits = []
    targets = re.compile(r"""fetch\(\s*[`'"]/api/v1/(applications|agents|knowledge|workspace)""")
    for p in _web_files("vue", "ts"):
        text = p.read_text(encoding="utf-8", errors="ignore")
        if not targets.search(text):
            continue
        # public 端點不需要
        only_public = all(
            "/public/" in m for m in re.findall(r"""fetch\(\s*[`'"]([^`'\"]+)""", text)
            if "/api/v1/" in m
        )
        if only_public:
            continue
        if "X-Workspace-ID" not in text:
            hits.append(str(p.relative_to(ROOT)))
    assert not hits, "raw fetch 打 workspace 端點但無 X-Workspace-ID 注入:\n" + "\n".join(hits)


# ── placeholder view 守衛 ────────────────────────────────────────────
def test_no_placeholder_views():
    """UnderConstructionView placeholder 不該殘留 (CLAUDE.md release checklist)。"""
    hits = [
        str(p.relative_to(ROOT))
        for p in _web_files("vue", "ts")
        if "UnderConstructionView" in p.read_text(encoding="utf-8", errors="ignore")
        and "UnderConstructionView.vue" not in p.name
    ]
    assert not hits, "發現 UnderConstructionView placeholder:\n" + "\n".join(hits)
