"""E2E smoke — 對 live stack 跑完整使用者流程，抓回歸。

GH-hosted runner 跑不動整套 (embedder 要下載 Ollama models)，所以這支是:
- 本機 / self-hosted runner 手動跑: `python tests/e2e_smoke.py`
- CI workflow_dispatch 手動觸發 (rag-eval.yml 同模式)

覆蓋這輪實際踩過的 bug 的關鍵路徑:
- 登入 / workspace header (v5.9.x 一連串)
- agents 列表 (gateway workspace 注入 v5.9.10)
- 對話建立 + 串流 (conversation_id vs id v5.9.11, SSE CRLF v5.9.32)
- **串流換行保留 (v5.11.6 — 地端模型純換行 token 經 SSE 失真，答案擠成一坨)**
- KB 建立 (gateway knowledge 注入 v5.9.16)
- **ingest → 檢索 回歸 (上傳已知事實 → 等 READY → search 撈回 — RAG 核心管線)**
- 應用建立 + RAG 對話 (ApplicationAgent LLM v5.9.28)

用法:
    BASE=http://localhost ADMIN_PW=Admin@2026 python tests/e2e_smoke.py
非 0 exit = 有 case 失敗。
"""
from __future__ import annotations

import os
import sys
import time
import uuid

import httpx

BASE = os.environ.get("BASE", "http://localhost").rstrip("/")
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PW = os.environ.get("ADMIN_PW", "Admin@2026")
INGEST_TIMEOUT = int(os.environ.get("E2E_INGEST_TIMEOUT", "120"))

_passed: list[str] = []
_failed: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    (_passed if cond else _failed).append(name)
    mark = "✅" if cond else "❌"
    print(f"{mark} {name}" + (f" — {detail}" if detail and not cond else ""))


def sse_assistant_text(stream) -> str:
    """事件感知 SSE 解析：累積一個 event 的 data: 行，遇空行用 \\n 重組（同前端/中繼）。

    只收 token 事件的文字（略過 citations/done/error）。**關鍵**：要用 \\n 重組
    多行 data，才能忠實反映換行是否保留 —— naive 的「逐行 lstrip 後 join」會把
    換行吃掉，根本測不出 v5.11.6 那種「擠成一坨」的回歸。
    """
    out: list[str] = []
    ev = ""
    data_lines: list[str] = []

    def flush():
        nonlocal ev, data_lines
        if not ev and not data_lines:
            return
        data = "\n".join(data_lines)
        etype, ev, data_lines = ev, "", []
        if etype in ("citations", "done", "error"):
            return
        if data.strip() in ("", "[DONE]") or data.lstrip().startswith("["):
            return
        out.append(data)

    for raw in stream.iter_lines():
        line = raw.rstrip("\r") if isinstance(raw, str) else raw.decode().rstrip("\r")
        if line == "":
            flush()
            continue
        if line.startswith("event:"):
            ev = line[6:].strip()
        elif line.startswith("data:"):
            s = line[5:]
            data_lines.append(s[1:] if s.startswith(" ") else s)
    flush()
    return "".join(out)


def main() -> int:
    c = httpx.Client(base_url=BASE, timeout=90.0)

    # 1. 登入
    r = c.post("/api/v1/auth/login", json={"username": ADMIN_USER, "password": ADMIN_PW})
    token = (r.json().get("data") or {}).get("access_token")
    check("login", bool(token), f"HTTP {r.status_code}")
    if not token:
        _summary()
        return 1
    H = {"Authorization": f"Bearer {token}"}

    # workspace id
    r = c.get("/api/v1/workspaces", headers=H)
    _d = r.json().get("data")
    ws = (_d.get("items") if isinstance(_d, dict) else _d) or []
    ws_id = ws[0].get("id") if ws else "00000000-0000-0000-0000-000000000001"
    HW = {**H, "X-Workspace-ID": ws_id}
    check("workspaces", bool(ws_id))

    # 2. agents 列表 (gateway workspace 注入)
    r = c.get("/api/v1/agents/", headers=HW)
    agents = r.json().get("data") or []
    check("agents_list", r.status_code == 200 and len(agents) >= 1, f"HTTP {r.status_code}")
    scenario = agents[0]["scenario_id"] if agents else "official_doc"

    # 3. 對話建立 + 串流 (conversation_id, SSE CRLF, 換行保留 v5.11.6)
    r = c.post("/api/v1/chat/conversations", headers=HW,
               json={"scenario_id": scenario, "kb_ids": []})
    conv_id = (r.json().get("data") or {}).get("conversation_id")
    check("conv_create", bool(conv_id), f"HTTP {r.status_code}")
    if conv_id:
        # 用「條列」prompt 逼出多段落答案 → 驗證換行有沒有穿過 SSE 鏈活著
        prompt = "請用條列式列出台灣三個直轄市，每個直轄市獨立一行，並各加一句說明。"
        with c.stream("POST", f"/api/v1/chat/conversations/{conv_id}/messages/stream",
                      headers=HW, json={"content": prompt}) as s:
            text_ans = sse_assistant_text(s)
        check("chat_stream_tokens", len(text_ans.strip()) > 0, f"got {len(text_ans)} chars")
        check("chat_no_cr_in_token", "\r" not in text_ans, "答案含殘留 \\r (SSE CRLF bug)")
        # v5.11.6 回歸守衛：條列答案應有換行（地端模型純換行 token 不該被 SSE 吃掉）
        check("chat_newlines_preserved", text_ans.count("\n") >= 1,
              f"條列答案無換行 → 擠成一坨 (v5.11.6 回歸)；ans[:80]={text_ans[:80]!r}")

    # 4. KB 建立 (gateway knowledge 注入)
    kb_name = f"e2e-{uuid.uuid4().hex[:8]}"
    r = c.post("/api/v1/knowledge/bases", headers=HW,
               json={"name": kb_name, "description": "e2e smoke"})
    kb_id = (r.json().get("data") or {}).get("id")
    check("kb_create", bool(kb_id), f"HTTP {r.status_code}: {r.text[:120]}")

    # 4b. ingest → 檢索 回歸（RAG 核心管線：上傳已知事實 → 等 READY → search 撈回）
    marker = f"ZEBRA{uuid.uuid4().hex[:6].upper()}"   # 獨特標記，確保不是撞既有資料
    if kb_id:
        fact = (
            f"本測試文件唯一識別碼：{marker}。\n"
            f"員工特休假規定：每位正職員工每年享有特休假 14 天，"
            f"須於請假系統提前 3 個工作天申請，並經直屬主管核准後生效。\n"
        ).encode("utf-8")
        files = {"file": (f"{marker}.txt", fact, "text/plain")}
        r = c.post(f"/api/v1/knowledge/documents/{kb_id}/upload", headers=HW, files=files)
        _dd = r.json().get("data") or {}
        doc_id = _dd.get("document_id") or _dd.get("id")   # upload 回 document_id
        check("doc_upload", bool(doc_id), f"HTTP {r.status_code}: {r.text[:120]}")

        # 輪詢文件直到 READY（embedding 完成）；無 FAILED 狀態，錯誤走 error_message
        ready, err = False, ""
        deadline = time.time() + INGEST_TIMEOUT
        while doc_id and time.time() < deadline:
            rr = c.get(f"/api/v1/knowledge/documents/{kb_id}", headers=HW)
            data = rr.json().get("data")
            docs = (data.get("items") if isinstance(data, dict) else data) or []
            mine = next((d for d in docs if str(d.get("id")) == str(doc_id)), None)
            if str((mine or {}).get("status", "")).lower() == "ready":
                ready = True
                break
            if (mine or {}).get("error_message"):
                err = mine["error_message"]
                break
            time.sleep(2)
        check("doc_ingest_ready", ready, err or f"{INGEST_TIMEOUT}s 內未 READY")

        # 檢索回歸：用語意相近但非逐字的 query，撈回剛才那篇
        if ready:
            r = c.post("/api/v1/knowledge/search", headers=HW,
                       json={"query": "員工特休假有幾天、怎麼申請？", "kb_ids": [kb_id], "top_k": 5})
            cites = ((r.json().get("data") or {}).get("citations")) or []
            blob = " ".join(x.get("content", "") for x in cites)
            check("rag_retrieve", r.status_code == 200 and len(cites) >= 1,
                  f"HTTP {r.status_code}, citations={len(cites)}")
            check("rag_retrieve_relevant", (marker in blob) or ("14" in blob),
                  f"撈回內容不含已知事實；citations={len(cites)}")

    # 5. 應用建立 + RAG 對話 (ApplicationAgent)
    app_id = None
    if kb_id:
        r = c.post("/api/v1/applications", headers=HW, json={
            "name": f"{kb_name} 助理", "type": "simple",
            "knowledge_base_ids": [kb_id], "system_prompt": "你是測試助理",
        })
        app_id = (r.json().get("data") or {}).get("id")
        check("app_create", bool(app_id), f"HTTP {r.status_code}")
    if app_id:
        with c.stream("POST", f"/api/v1/applications/{app_id}/chat", headers=HW,
                      json={"session_id": "t", "messages": [{"role": "user", "content": "你好"}], "kb_ids": []}) as s:
            atoks = [line[5:].lstrip() for line in s.iter_lines()
                     if line.startswith("data:") and line[5:].lstrip() not in ("", "[DONE]")
                     and not line[5:].lstrip().startswith("[")]
        check("app_chat_stream", len("".join(atoks).strip()) > 0, f"got {len(atoks)} tokens")

    # 清理測試資料
    if app_id:
        c.request("DELETE", f"/api/v1/applications/{app_id}", headers=HW)
    if kb_id:
        c.request("DELETE", f"/api/v1/knowledge/bases/{kb_id}", headers=HW)
    if conv_id:
        c.request("DELETE", f"/api/v1/chat/conversations/{conv_id}", headers=HW)

    return _summary()


def _summary() -> int:
    print(f"\n── E2E smoke: {len(_passed)} passed, {len(_failed)} failed ──")
    if _failed:
        print("FAILED:", ", ".join(_failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
