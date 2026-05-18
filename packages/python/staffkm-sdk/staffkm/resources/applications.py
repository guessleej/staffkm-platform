"""Applications resource."""
from __future__ import annotations

import httpx


class ApplicationsResource:
    def __init__(self, http: httpx.Client):
        self._http = http

    def list(self) -> list[dict]:
        r = self._http.get("/api/v1/applications")
        r.raise_for_status()
        return r.json().get("data") or []

    def create(self, name: str, type: str = "chat", **kwargs) -> dict:
        body = {"name": name, "type": type, **kwargs}
        r = self._http.post("/api/v1/applications", json=body)
        r.raise_for_status()
        return r.json().get("data") or r.json()

    def get(self, application_id: str) -> dict:
        r = self._http.get(f"/api/v1/applications/{application_id}")
        r.raise_for_status()
        return r.json().get("data") or r.json()

    def run(self, application_id: str, inputs: dict) -> dict:
        r = self._http.post(
            f"/api/v1/applications/{application_id}/run",
            json={"inputs": inputs},
        )
        r.raise_for_status()
        return r.json()
