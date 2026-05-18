"""Plugin interfaces — v4.3.

Plugin types:
- BaseNode      — custom workflow node (執行邏輯)
- BaseProvider  — custom LLM / media provider
- BaseHook      — workflow lifecycle hook (before_run / after_node / after_run)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator


class PluginContext:
    """Plugin 執行時可用的 context（注入 caller workspace / user / DB session...）。"""

    def __init__(
        self,
        *,
        workspace_id: str,
        user_id: str | None = None,
        session_factory: Any = None,
        settings: dict | None = None,
    ):
        self.workspace_id = workspace_id
        self.user_id = user_id
        self.session_factory = session_factory
        self.settings = settings or {}


class BaseNode(ABC):
    """Custom workflow node。"""

    node_type: str = ""  # 唯一識別（e.g. "weather_lookup"）

    @abstractmethod
    async def execute(
        self, config: dict, ctx: PluginContext, inputs: dict
    ) -> dict | AsyncIterator[dict]:
        """執行 node 邏輯，回 result dict 或 stream events。"""


class BaseProvider(ABC):
    """Custom LLM provider（與 services/agent BaseProvider 介面對齊但獨立 import）。"""

    provider_type: str = ""

    @abstractmethod
    async def chat(self, model: str, messages: list[dict], **kwargs) -> dict: ...

    async def chat_stream(
        self, model: str, messages: list[dict], **kwargs
    ) -> AsyncIterator[str]:
        result = await self.chat(model, messages, **kwargs)
        yield result.get("text", "")


class BaseHook(ABC):
    """Workflow lifecycle hook — 在 run 前/後 / node 前/後 觸發。"""

    hook_type: str = ""  # before_run / after_run / before_node / after_node
    priority: int = 100  # 低 = 先跑

    @abstractmethod
    async def handle(self, event: dict, ctx: PluginContext) -> None: ...
