"""Plugin runtime integration — v4.3.

啟動時 load `/app/plugins/`（可用 STAFFKM_PLUGINS_DIR 覆寫）內所有 plugin。

TODO (v4.4): executor.py 的 _exec_* dispatch 鏈最後加 fallback：
    from app.core.plugin_loader import get_plugin_node
    pnode = get_plugin_node(node_type)
    if pnode:
        from staffkm_plugin_sdk.base import PluginContext
        ctx = PluginContext(
            workspace_id=self.workspace_id,
            user_id=self.user_id,
            session_factory=lambda: _db._session_factory,
        )
        result = await pnode.execute(config, ctx, context)
        if isinstance(result, dict):
            context.update(result)

本 PR 故意不動 executor.py（避免 break workflow runtime），只 load + expose registry。
"""
from __future__ import annotations

import os
from pathlib import Path

import structlog

try:
    from staffkm_plugin_sdk.runtime import LoadedPlugin, load_plugins_from_dir
except Exception:  # SDK 沒裝 → 整個 plugin 機制 noop（不影響 agent 啟動）
    LoadedPlugin = None  # type: ignore[assignment,misc]
    load_plugins_from_dir = None  # type: ignore[assignment]

log = structlog.get_logger()

PLUGINS_DIR = Path(os.environ.get("STAFFKM_PLUGINS_DIR", "/app/plugins"))

# 全域 plugin registry（lifespan 啟動時填）
_LOADED_PLUGINS: dict[str, "LoadedPlugin"] = {}


def load_all_plugins() -> dict[str, "LoadedPlugin"]:
    global _LOADED_PLUGINS
    if load_plugins_from_dir is None:
        log.info("plugin_sdk_not_installed_skip")
        _LOADED_PLUGINS = {}
        return _LOADED_PLUGINS
    try:
        _LOADED_PLUGINS = load_plugins_from_dir(PLUGINS_DIR)
    except Exception as e:
        # plugin load 出包不能 fail 整個 agent；log + 空 registry
        log.warning("plugins_load_failed", error=str(e))
        _LOADED_PLUGINS = {}
    log.info("plugins_loaded_total", count=len(_LOADED_PLUGINS), dir=str(PLUGINS_DIR))
    return _LOADED_PLUGINS


def get_loaded_plugins() -> dict[str, "LoadedPlugin"]:
    return _LOADED_PLUGINS


def get_plugin_node(node_type: str):
    """Look up a custom node by type (給未來 executor 接 plugin 用)。"""
    for p in _LOADED_PLUGINS.values():
        if node_type in p.nodes:
            return p.nodes[node_type]
    return None


def get_plugin_provider(provider_type: str):
    for p in _LOADED_PLUGINS.values():
        if provider_type in p.providers:
            return p.providers[provider_type]
    return None
