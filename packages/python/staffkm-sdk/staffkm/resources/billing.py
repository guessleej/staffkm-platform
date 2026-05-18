"""Billing resource — admin scope."""
from __future__ import annotations

import httpx


class _Users:
    def __init__(self, http: httpx.Client):
        self._http = http

    def list(self, month: str | None = None) -> list[dict]:
        params = {"month": month} if month else {}
        r = self._http.get("/api/v1/billing/users", params=params)
        r.raise_for_status()
        return r.json().get("data") or []

    def detail(self, user_id: str, month: str | None = None) -> dict:
        params = {"month": month} if month else {}
        r = self._http.get(f"/api/v1/billing/users/{user_id}", params=params)
        r.raise_for_status()
        return r.json().get("data") or r.json()

    def csv(self, month: str | None = None) -> bytes:
        params = {"month": month} if month else {}
        r = self._http.get("/api/v1/billing/users.csv", params=params)
        r.raise_for_status()
        return r.content


class BillingResource:
    def __init__(self, http: httpx.Client):
        self.users = _Users(http)
