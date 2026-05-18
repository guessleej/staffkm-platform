"""Auth resource — login / refresh / me."""
from __future__ import annotations

import httpx


class AuthResource:
    def __init__(self, http: httpx.Client):
        self._http = http

    def login(self, username: str, password: str) -> dict:
        r = self._http.post("/api/v1/auth/login", json={
            "username": username,
            "password": password,
        })
        r.raise_for_status()
        return r.json()

    def refresh(self, refresh_token: str) -> dict:
        r = self._http.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        r.raise_for_status()
        return r.json()

    def me(self) -> dict:
        r = self._http.get("/api/v1/auth/me")
        r.raise_for_status()
        return r.json()
