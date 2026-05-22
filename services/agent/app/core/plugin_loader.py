"""Plugin runtime integration — v4.3 / v5.10.12。

啟動時 load `/app/plugins/`（可用 STAFFKM_PLUGINS_DIR 覆寫）內所有 plugin。

v5.10.12：executor.py dispatch 鏈尾端已接 plugin fallback — 非內建 node_type
會經 `get_plugin_node(node_type)` 取 BaseNode，注入 PluginContext 執行
（見 WorkflowExecutor._exec_plugin_node）。本檔負責 load + expose registry。
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
