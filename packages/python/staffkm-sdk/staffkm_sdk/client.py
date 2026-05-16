"""StaffKMClient — 同步 + 串流 client。

設計：
- 同步用 httpx.Client；串流用 .stream()
- 全部 endpoint 都走 workspace-scoped URL
- 401 → AuthError；429 → QuotaExceeded；其餘 5xx → StaffKMError
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterator

import httpx

from .errors import AuthError, QuotaExceeded, StaffKMError


@dataclass
class ChatResponse:
    content: str
    citations: list[dict]
    usage: dict | None = None


class _KnowledgeAPI:
    def __init__(self, c: "StaffKMClient"): self._c = c
    def list(self):    return self._c._get("/knowledge").get("data") or []
    def documents(self, kb_id: str): return self._c._get(f"/knowledge/{kb_id}/documents").get("data") or []
    def search(self, kb_id: str, query: str, top_k: int = 5):
        return self._c._post(f"/knowledge/{kb_id}/search",
                             {"query": query, "top_k": top_k}).get("data") or []


class _UsageAPI:
    def __init__(self, c: "StaffKMClient"): self._c = c
    def summary(self):       return self._c._get("/usage/summary").get("data")
    def logs(self, page: int = 1, page_size: int = 50):
        return self._c._get("/usage/logs", params={"page": page, "page_size": page_size}).get("data")
    def quota(self):         return self._c._get("/quota").get("data")
    def set_quota(self, *, monthly_token_cap: int | None = None, monthly_cost_cap_usd: float | None = None):
        return self._c._put("/quota", {
            "monthly_token_cap":    monthly_token_cap,
            "monthly_cost_cap_usd": monthly_cost_cap_usd,
        }).get("data")


class _AppsAPI:
    def __init__(self, c: "StaffKMClient"): self._c = c
    def list(self):           return self._c._get("/applications").get("data") or []
    def get(self, app_id):    return self._c._get(f"/applications/{app_id}").get("data")
    def create(self, **kw):   return self._c._post("/applications", kw).get("data")


class StaffKMClient:
    """staffKM v2 API client.

    Parameters
    ----------
    base_url : str
        e.g. ``https://staffkm.example.com``
    api_key : str
        從 ``/admin/api-keys`` 取得的 key（會放到 ``Authorization`` header）
    workspace_id : str
        所有 endpoint 會自動帶上此 prefix
    timeout : float
        single request timeout（SSE 不受此限）
    """

    def __init__(
        self,
        base_url: str,
        *,
        api_key: str,
        workspace_id: str,
        timeout: float = 30.0,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._prefix = f"/api/v1/workspace/{workspace_id}"
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self._http = httpx.Client(timeout=timeout, headers=self._headers)

        self.knowledge = _KnowledgeAPI(self)
        self.usage     = _UsageAPI(self)
        self.apps      = _AppsAPI(self)

    # ── 內部 HTTP 包裝 ──────────────────────────────────────────────
    def _url(self, path: str) -> str:
        return f"{self._base}{self._prefix}{path}"

    def _raise(self, r: httpx.Response) -> None:
        if r.status_code < 400:
            return
        try:
            data = r.json()
        except Exception:
            data = {"detail": r.text}
        msg = data.get("detail") or data.get("message") or r.text
        if r.status_code in (401, 403):
            raise AuthError(str(msg), r.status_code, data)
        if r.status_code == 429:
            raise QuotaExceeded(str(msg), r.status_code, data)
        raise StaffKMError(str(msg), r.status_code, data)

    def _get(self, path: str, **kw):
        r = self._http.get(self._url(path), **kw); self._raise(r); return r.json()

    def _post(self, path: str, body: dict | None = None, **kw):
        r = self._http.post(self._url(path), json=body or {}, **kw); self._raise(r); return r.json()

    def _put(self, path: str, body: dict | None = None, **kw):
        r = self._http.put(self._url(path), json=body or {}, **kw); self._raise(r); return r.json()

    # ── Chat ────────────────────────────────────────────────────────
    def chat(self, *, app_id: str, message: str, kb_ids: list[str] | None = None) -> ChatResponse:
        """非串流：把 SSE 累積成一次回傳。"""
        content_parts: list[str] = []
        citations: list[dict] = []
        for ev in self._chat_events(app_id=app_id, message=message, kb_ids=kb_ids):
            if ev.get("event") == "token":
                content_parts.append(ev.get("data") or "")
            elif ev.get("event") == "citations":
                try: citations = json.loads(ev.get("data") or "[]")
                except Exception: pass
        return ChatResponse(content="".join(content_parts), citations=citations)

    def chat_stream(self, *, app_id: str, message: str, kb_ids: list[str] | None = None) -> Iterator[str]:
        """SSE 串流；只 yield text chunks。"""
        for ev in self._chat_events(app_id=app_id, message=message, kb_ids=kb_ids):
            if ev.get("event") == "token":
                yield ev.get("data") or ""

    def _chat_events(self, *, app_id: str, message: str, kb_ids: list[str] | None) -> Iterator[dict]:
        body = {"messages": [{"role": "user", "content": message}], "kb_ids": kb_ids or []}
        with self._http.stream(
            "POST",
            self._url(f"/agents/applications/{app_id}/chat"),
            json=body,
        ) as r:
            self._raise(r)
            event_name: str | None = None
            for line in r.iter_lines():
                if not line:
                    event_name = None
                    continue
                if line.startswith("event:"):
                    event_name = line[6:].strip()
                elif line.startswith("data:"):
                    data = line[5:].strip()
                    if data == "[DONE]":
                        return
                    yield {"event": event_name or "message", "data": data}

    def close(self) -> None:
        self._http.close()

    def __enter__(self): return self
    def __exit__(self, *_): self.close()
