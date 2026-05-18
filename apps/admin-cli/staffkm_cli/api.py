"""HTTP client wrapper — uses ~/.staffkm/credentials.json (v4.4 D).

對既有 staffkm-sdk 互補：sdk 走 env/api-key；本 module 走 cred file + JWT。
"""
from __future__ import annotations

import httpx

from .config import get_or_die


def client() -> httpx.Client:
    """Return an authenticated httpx client (caller is responsible for closing)."""
    cred = get_or_die()
    headers = {"Authorization": f"Bearer {cred['token']}"}
    if cred.get("workspace_id"):
        headers["X-Workspace-ID"] = cred["workspace_id"]
    return httpx.Client(base_url=cred["base"], headers=headers, timeout=30.0)
