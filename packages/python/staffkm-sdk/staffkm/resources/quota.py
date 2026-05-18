"""Quota resource."""
from __future__ import annotations

import httpx


class QuotaResource:
    def __init__(self, http: httpx.Client):
        self._http = http

    def summary(self) -> dict:
        r = self._http.get("/api/v1/quota/summary")
        r.raise_for_status()
        return r.json().get("data") or r.json()

    def set(
        self,
        *,
        monthly_token_cap: int | None = None,
        monthly_cost_cap_usd: float | None = None,
    ) -> dict:
        body = {
            "monthly_token_cap": monthly_token_cap,
            "monthly_cost_cap_usd": monthly_cost_cap_usd,
        }
        r = self._http.put("/api/v1/quota", json=body)
        r.raise_for_status()
        return r.json().get("data") or r.json()

    def list(self) -> list[dict]:
        """Admin: list all workspace quotas."""
        r = self._http.get("/api/v1/admin/quota")
        r.raise_for_status()
        return r.json().get("data") or []
