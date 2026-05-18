"""staffKM Plugin SDK — v4.3 Theme C.

第三方寫 custom node / provider / hook 用的 SDK。

公開介面：
    from staffkm_plugin_sdk import BaseNode, BaseProvider, BaseHook, PluginContext
    from staffkm_plugin_sdk import PluginManifest
    from staffkm_plugin_sdk import load_plugin, load_plugins_from_dir
"""
from .base import BaseHook, BaseNode, BaseProvider, PluginContext
from .manifest import PluginManifest
from .runtime import LoadedPlugin, load_plugin, load_plugins_from_dir

__version__ = "0.1.0"

__all__ = [
    "BaseHook",
    "BaseNode",
    "BaseProvider",
    "PluginContext",
    "PluginManifest",
    "LoadedPlugin",
    "load_plugin",
    "load_plugins_from_dir",
    "__version__",
]
