"""Knowledge base resource."""
from __future__ import annotations

from typing import IO
import httpx


class _KBs:
    def __init__(self, http: httpx.Client):
        self._http = http

    def list(self) -> list[dict]:
        r = self._http.get("/api/v1/knowledge")
        r.raise_for_status()
        return r.json().get("data") or []

    def create(self, name: str, description: str | None = None) -> dict:
        r = self._http.post("/api/v1/knowledge", json={
            "name": name,
            "description": description or "",
        })
        r.raise_for_status()
        return r.json().get("data") or r.json()


class _Docs:
    def __init__(self, http: httpx.Client):
        self._http = http

    def upload(self, kb_id: str, file: IO[bytes], filename: str) -> dict:
        files = {"file": (filename, file)}
        r = self._http.post(f"/api/v1/knowledge/{kb_id}/documents", files=files)
        r.raise_for_status()
        return r.json().get("data") or r.json()


class KnowledgeResource:
    def __init__(self, http: httpx.Client):
        self._http = http
        self.kbs = _KBs(http)
        self.docs = _Docs(http)

    def hit_test(self, kb_id: str, query: str, top_k: int = 5) -> list[dict]:
        r = self._http.post(f"/api/v1/knowledge/{kb_id}/hit_test", json={
            "query": query,
            "top_k": top_k,
        })
        r.raise_for_status()
        return r.json().get("data") or []
