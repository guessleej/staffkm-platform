"""Main StaffKM client — v4.5 E."""
from __future__ import annotations

import httpx

from .resources import (
    auth,
    workspaces,
    knowledge,
    applications,
    chat,
    quota,
    billing,
    plugins,
)


class StaffKM:
    """Synchronous client for staffKM API."""

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        token: str | None = None,
        workspace_id: str | None = None,
        timeout: float = 30.0,
    ):
        if not api_key and not token:
            raise ValueError("must provide either api_key or token")
        headers: dict[str, str] = {}
        if api_key:
            headers["X-API-Key"] = api_key
        elif token:
            headers["Authorization"] = f"Bearer {token}"
        if workspace_id:
            headers["X-Workspace-ID"] = workspace_id
        self._http = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers=headers,
            timeout=timeout,
        )
        self.workspace_id = workspace_id

        self.auth = auth.AuthResource(self._http)
        self.workspaces = workspaces.WorkspacesResource(self._http)
        self.knowledge = knowledge.KnowledgeResource(self._http)
        self.applications = applications.ApplicationsResource(self._http)
        self.chat = chat.ChatResource(self._http)
        self.quota = quota.QuotaResource(self._http)
        self.billing = billing.BillingResource(self._http)
        self.plugins = plugins.PluginsResource(self._http)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "StaffKM":
        return self

    def __exit__(self, *a) -> None:
        self.close()


class AsyncStaffKM:
    """Async client — same API but uses httpx.AsyncClient.

    v4.5 first cut: only the underlying client is wired; async resource
    modules ship in v4.6. For now use ``self._http`` directly if you need
    async access.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        token: str | None = None,
        workspace_id: str | None = None,
        timeout: float = 30.0,
    ):
        if not api_key and not token:
            raise ValueError("must provide either api_key or token")
        headers: dict[str, str] = {}
        if api_key:
            headers["X-API-Key"] = api_key
        elif token:
            headers["Authorization"] = f"Bearer {token}"
        if workspace_id:
            headers["X-Workspace-ID"] = workspace_id
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers=headers,
            timeout=timeout,
        )
        self.workspace_id = workspace_id

    async def close(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> "AsyncStaffKM":
        return self

    async def __aexit__(self, *a) -> None:
        await self.close()
