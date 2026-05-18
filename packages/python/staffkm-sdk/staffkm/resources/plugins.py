"""Plugins resource."""
from __future__ import annotations

import httpx


class PluginsResource:
    def __init__(self, http: httpx.Client):
        self._http = http

    def list(self) -> list[dict]:
        r = self._http.get("/api/v1/plugins")
        r.raise_for_status()
        return r.json().get("data") or []

    def reload(self) -> dict:
        r = self._http.post("/api/v1/plugins/reload")
        r.raise_for_status()
        return r.json()
