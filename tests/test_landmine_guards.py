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
# 同時涵蓋兩種寫法（v5.10.5：補 f-string 內插變體，原本只抓字面 :name）：
#   - 字面 named param：   :config::jsonb
#   - f-string 內插 param：:{k}::jsonb  ← 曾因此逃過 grep，害 generic CRUD 全掛
_TYPES = "jsonb|vector|uuid|int|text|timestamptz|date|inet|bool"
_PARAM_CAST = re.compile(
    rf":(?:[a-z_][a-z0-9_]*|\{{[a-z_][a-z0-9_]*\}})::(?:{_TYPES})"
)


def test_no_asyncpg_param_cast():
    """:param::jsonb / :{var}::jsonb — asyncpg dialect 不認，必須用 CAST(:param AS type)。"""
    pat = _PARAM_CAST
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


# ── admin/models 預設模型「真生效」守衛（CLAUDE.md §11）─────────────────
# 雷：system_settings.default.* 一度只是 advisory（runtime 讀 env、選了不生效）。
# 已接通的 default.{llm,vision,rerank} 必須在 runtime 端有 resolver 且被呼叫，
# 否則 UI 看起來會生效、實際沒接 → 使用者「選了沒反應」。
def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def test_default_settings_wired_to_runtime():
    base_agent = _read(SERVICES / "agent/app/core/base_agent.py")
    app_agent = _read(SERVICES / "agent/app/core/application_agent.py")
    runtime_models = _read(SERVICES / "knowledge/app/core/runtime_models.py")
    process_doc = _read(SERVICES / "knowledge/app/tasks/process_document.py")
    search_py = _read(SERVICES / "knowledge/app/api/search.py")
    if not base_agent:  # repo 結構不符就跳過（不誤殺外部 checkout）
        return

    fail = []
    # default.llm → base_agent.resolve_system_llm 定義 + 被呼叫（def + call ≥ 2）
    if base_agent.count("resolve_system_llm") < 2 or "default.llm" not in base_agent:
        fail.append("base_agent 未把 default.llm 接到 runtime（resolve_system_llm 未定義/未呼叫）")
    # application 對話也要 fallback 系統預設
    if app_agent and app_agent.count("_resolve_default_llm_model_id") < 2:
        fail.append("application_agent 未 fallback 系統預設 LLM（_resolve_default_llm_model_id）")
    # default.vision → runtime_models.resolve_vision_ocr 定義 + process_document 呼叫
    if "def resolve_vision_ocr" not in runtime_models or "default.vision" not in runtime_models:
        fail.append("runtime_models 缺 resolve_vision_ocr / default.vision")
    if "resolve_vision_ocr" not in process_doc:
        fail.append("process_document 未呼叫 resolve_vision_ocr（vision OCR 退回 advisory）")
    # default.rerank → runtime_models.resolve_reranker 定義 + search 呼叫
    if "def resolve_reranker" not in runtime_models or "default.rerank" not in runtime_models:
        fail.append("runtime_models 缺 resolve_reranker / default.rerank")
    if "resolve_reranker" not in search_py:
        fail.append("search 未呼叫 resolve_reranker（reranker 退回 advisory）")
    assert not fail, "default.* 設定未接通 runtime（會變『選了沒反應』）:\n  - " + "\n  - ".join(fail)


# ── ollama base_url /v1 契約（v5.11.x 雷）──────────────────────────────
def test_ollama_registry_default_base_url_no_v1():
    """ollama verify 走原生 /api/tags → registry 預設 base_url 不可帶 /v1
    （帶了會變 /v1/api/tags → 404；曾把『測試』按鈕弄紅）。"""
    reg = SERVICES / "agent/app/core/providers/registry.py"
    if not reg.exists():
        return
    m = re.search(r'ProviderMeta\(\s*"ollama".*?default_base_url\s*=\s*"([^"]*)"',
                  reg.read_text(encoding="utf-8", errors="ignore"), re.DOTALL)
    assert m, "registry 找不到 ollama ProviderMeta default_base_url"
    assert not m.group(1).rstrip("/").endswith("/v1"), \
        f"ollama 預設 base_url 不該帶 /v1（verify 走 /api/tags）：{m.group(1)}"


# ── ollama 模型清單不寫死（v5.11.x 幽靈模型雷）──────────────────────────
def test_no_hardcoded_ollama_model_seed():
    """ollama 模型靠 /api/tags 動態同步，不可在 seed dict 寫死 → 否則出現 host 上
    沒有的『幽靈模型』，且 agent 重啟一直種回來。"""
    hits = []
    for rel in ["services/agent/app/data/model_pricing.py", "services/auth/app/api/models.py"]:
        p = ROOT / rel
        if p.exists() and '"ollama": [' in p.read_text(encoding="utf-8", errors="ignore"):
            hits.append(rel)
    assert not hits, ("發現寫死的 ollama 模型 seed（改靠 /api/tags 動態同步）:\n" + "\n".join(hits))


# ── get_session 不可當 async context manager（v5.11.x 雷）────────────────
def test_no_async_with_get_session():
    """get_session 是 FastAPI 依賴用的 async generator；非 endpoint 直接 `async with
    get_session()` 會炸 'async_generator does not support ... context manager'。
    應改用底層 _db._session_factory()。"""
    pat = re.compile(r"async\s+with\s+get_session\s*\(")
    hits = []
    for p in _py_files(SERVICES, PKGS):
        for i, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            if pat.search(line):
                hits.append(f"{p.relative_to(ROOT)}:{i}")
    assert not hits, ("發現 `async with get_session()`（改用 _db._session_factory()）:\n"
                      + "\n".join(hits))


# ── Celery 任務 queue 路由守衛（v5.11.x 雷）──────────────────────────────
def test_celery_tasks_have_queue_route():
    """新 Celery task 沒在 task_routes 加 queue 路由 → 進 default queue，worker（-Q knowledge）
    收不到、任務永遠不跑（embedding reindex 曾中此雷）。每個 @celery_app.task(name=...) 的
    模組前綴都必須有對應 task_routes 規則。"""
    import re as _re
    tasks_dir = SERVICES / "knowledge/app/tasks"
    celery_app = tasks_dir / "celery_app.py"
    if not celery_app.exists():
        return
    routes_src = celery_app.read_text(encoding="utf-8", errors="ignore")
    # task_routes 的 key（如 "app.tasks.build_graph.*"）→ 取模組前綴
    routed = {m.rstrip(".*") for m in _re.findall(r'"(app\.tasks\.[a-z_]+)\.\*"', routes_src)}
    missing = []
    for p in tasks_dir.glob("*.py"):
        src = p.read_text(encoding="utf-8", errors="ignore")
        for name in _re.findall(r'name\s*=\s*"(app\.tasks\.[a-z_]+)\.[a-z_]+"', src):
            if name not in routed:
                missing.append(f"{p.name}: {name} 無 task_routes 路由")
    assert not missing, ("Celery task 缺 queue 路由（worker -Q 收不到）:\n  - " + "\n  - ".join(missing))


# ── API key 加密單一來源守衛（v5.12 雙加密統一）──────────────────────────
def test_no_raw_base64_on_api_key():
    """API key 一律走 staffkm_core.secrets.encrypt_secret/decrypt_secret，不可再 raw
    base64 編解（兩套不一致是既有債，v5.12 收斂）。掃同一行同時出現 base64.b64(de|en)code
    與 api_key → 視為 raw 編解碼漏網。"""
    pat = re.compile(r"base64\.b64(?:de|en)code")
    hits = []
    for p in _py_files(SERVICES, PKGS):
        # secrets.py 本身是唯一允許 base64 的地方（legacy 偵測）
        if p.name == "secrets.py":
            continue
        for i, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            if pat.search(line) and "api_key" in line:
                hits.append(f"{p.relative_to(ROOT)}:{i}: {line.strip()[:80]}")
    assert not hits, ("發現 API key 的 raw base64 編解碼（改走 staffkm_core.secrets）:\n  - "
                      + "\n  - ".join(hits))


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
