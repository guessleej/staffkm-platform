"""Plugin runtime loader — 給 agent service 從 plugin directory load。"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any

import structlog
import yaml

from .manifest import PluginManifest

log = structlog.get_logger()


class LoadedPlugin:
    def __init__(self, manifest: PluginManifest, root_dir: Path):
        self.manifest = manifest
        self.root_dir = root_dir
        self.nodes: dict[str, Any] = {}
        self.providers: dict[str, Any] = {}
        self.hooks: list[Any] = []


def load_plugin(plugin_dir: Path) -> LoadedPlugin | None:
    """Load manifest + import plugin Python modules。"""
    manifest_file = plugin_dir / "manifest.yaml"
    if not manifest_file.exists():
        log.warning("plugin_no_manifest", dir=str(plugin_dir))
        return None
    try:
        manifest = PluginManifest(**yaml.safe_load(manifest_file.read_text()))
    except Exception as e:
        log.error("plugin_manifest_invalid", dir=str(plugin_dir), error=str(e))
        return None

    # Add plugin_dir to sys.path 讓 import 找得到
    if str(plugin_dir) not in sys.path:
        sys.path.insert(0, str(plugin_dir))

    loaded = LoadedPlugin(manifest=manifest, root_dir=plugin_dir)

    # Load nodes
    for entry in manifest.nodes:
        try:
            mod_name, cls_name = entry.split(":")
            mod = importlib.import_module(mod_name)
            cls = getattr(mod, cls_name)
            instance = cls()
            loaded.nodes[instance.node_type] = instance
        except Exception as e:
            log.warning("plugin_node_load_failed", entry=entry, error=str(e))

    # Load providers
    for entry in manifest.providers:
        try:
            mod_name, cls_name = entry.split(":")
            mod = importlib.import_module(mod_name)
            cls = getattr(mod, cls_name)
            instance = cls()
            loaded.providers[instance.provider_type] = instance
        except Exception as e:
            log.warning("plugin_provider_load_failed", entry=entry, error=str(e))

    # Load hooks
    for entry in manifest.hooks:
        try:
            mod_name, cls_name = entry.split(":")
            mod = importlib.import_module(mod_name)
            cls = getattr(mod, cls_name)
            loaded.hooks.append(cls())
        except Exception as e:
            log.warning("plugin_hook_load_failed", entry=entry, error=str(e))

    log.info(
        "plugin_loaded",
        name=manifest.name,
        version=manifest.version,
        nodes=len(loaded.nodes),
        providers=len(loaded.providers),
        hooks=len(loaded.hooks),
    )
    return loaded


def load_plugins_from_dir(plugins_root: Path) -> dict[str, LoadedPlugin]:
    """Scan a directory of plugins (each subdirectory = one plugin)."""
    loaded: dict[str, LoadedPlugin] = {}
    if not plugins_root.exists():
        return loaded
    for plugin_dir in plugins_root.iterdir():
        if not plugin_dir.is_dir():
            continue
        p = load_plugin(plugin_dir)
        if p:
            loaded[p.manifest.name] = p
    return loaded
