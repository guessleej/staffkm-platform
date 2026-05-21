"""E2E smoke — 對 live stack 跑完整使用者流程，抓回歸。

GH-hosted runner 跑不動整套 (embedder 要下載 Ollama models)，所以這支是:
- 本機 / self-hosted runner 手動跑: `python tests/e2e_smoke.py`
- CI workflow_dispatch 手動觸發 (rag-eval.yml 同模式)

覆蓋這輪實際踩過的 33 bug 的關鍵路徑:
- 登入 / workspace header (v5.9.x 一連串)
- agents 列表 (gateway workspace 注入 v5.9.10)
- 對話建立 + 串流 (conversation_id vs id v5.9.11, SSE CRLF v5.9.32)
- KB 建立 (gateway knowledge 注入 v5.9.16)
- 應用建立 + RAG 對話 (ApplicationAgent LLM v5.9.28)

用法:
    BASE=http://localhost ADMIN_PW=Admin@2026 python tests/e2e_smoke.py
非 0 exit = 有 case 失敗。
"""
from __future__ import annotations

import json
import os
import sys
import uuid

import httpx

BASE = os.environ.get("BASE", "http://localhost").rstrip("/")
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PW = os.environ.get("ADMIN_PW", "Admin@2026")

_passed: list[str] = []
_failed: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    (_passed if cond else _failed).append(name)
    mark = "✅" if cond else "❌"
    print(f"{mark} {name}" + (f" — {detail}" if detail and not cond else ""))


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

    # 3. 對話建立 + 串流 (conversation_id, SSE CRLF)
    r = c.post("/api/v1/chat/conversations", headers=HW,
               json={"scenario_id": scenario, "kb_ids": []})
    conv_id = (r.json().get("data") or {}).get("conversation_id")
    check("conv_create", bool(conv_id), f"HTTP {r.status_code}")
    if conv_id:
        with c.stream("POST", f"/api/v1/chat/conversations/{conv_id}/messages/stream",
                      headers=HW, json={"content": "用5字介紹台灣"}) as s:
            tokens, had_cr_token = [], False
            for line in s.iter_lines():
                if line.startswith("data:"):
                    d = line[5:].lstrip()
                    if d and d != "[DONE]" and not d.startswith("["):
                        tokens.append(d)
                        if "\r" in d:
                            had_cr_token = True
        joined = "".join(tokens)
        check("chat_stream_tokens", len(joined.strip()) > 0, f"got {len(tokens)} tokens")
        check("chat_no_cr_in_token", not had_cr_token, "token 含殘留 \\r (SSE CRLF bug)")

    # 4. KB 建立 (gateway knowledge 注入)
    kb_name = f"e2e-{uuid.uuid4().hex[:8]}"
    r = c.post("/api/v1/knowledge/bases", headers=HW,
               json={"name": kb_name, "description": "e2e smoke"})
    kb_id = (r.json().get("data") or {}).get("id")
    check("kb_create", bool(kb_id), f"HTTP {r.status_code}: {r.text[:120]}")

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
