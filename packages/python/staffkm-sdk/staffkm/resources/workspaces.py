"""Workspaces resource."""
from __future__ import annotations

import httpx


class WorkspacesResource:
    def __init__(self, http: httpx.Client):
        self._http = http

    def list(self) -> list[dict]:
        r = self._http.get("/api/v1/workspaces")
        r.raise_for_status()
        return r.json().get("data") or []

    def create(self, name: str, slug: str | None = None) -> dict:
        body = {"name": name}
        if slug:
            body["slug"] = slug
        r = self._http.post("/api/v1/workspaces", json=body)
        r.raise_for_status()
        return r.json().get("data") or r.json()

    def get(self, workspace_id: str) -> dict:
        r = self._http.get(f"/api/v1/workspaces/{workspace_id}")
        r.raise_for_status()
        return r.json().get("data") or r.json()
